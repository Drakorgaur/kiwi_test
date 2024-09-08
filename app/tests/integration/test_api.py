import contextlib
import os
import time
import unittest
from collections.abc import Callable
from pathlib import Path

import environ
import httpx
from docker.context import ContextAPI
from docker.api import APIClient
from testcontainers.core.container import DockerContainer

from testcontainers.core.network import Network


@environ.config(prefix="TESTCONTAINERS")
class TestContConfig:
    project_dir: Path = environ.var(converter=Path)
    api_image: str = environ.var()
    proxy_image: str = environ.var(default="nginx:alpine")


class TestContainers(unittest.TestCase):
    config: TestContConfig
    cleanup: Callable[[], None]  # closure cleanup function, see setUpClass

    api: DockerContainer
    proxy: DockerContainer

    @classmethod
    def setUpClass(cls):
        cls.config: TestContConfig = environ.to_config(TestContConfig)

        if not os.environ.get("CI"):
            docker_host = ContextAPI.get_current_context().Host
            os.environ["DOCKER_HOST"] = docker_host
            client = APIClient(base_url=docker_host)
        else:
            client = APIClient()

        socket_vol = "socket_vol"
        cache_vol = "cache_vol"
        client.create_volume(socket_vol)
        client.create_volume(cache_vol)

        network = Network().create()

        def cleanup():
            client.remove_volume(socket_vol)
            client.remove_volume(cache_vol)
            network.remove()

        cls.cleanup = cleanup

        api = DockerContainer(cls.config.api_image, user=0)
        proxy = DockerContainer(cls.config.proxy_image)

        api.with_network(network)
        proxy.with_network(network)

        api.with_volume_mapping(socket_vol, "/www/run/", mode="rw")
        cache_dir = "/tmp/cache"
        api.with_volume_mapping(cache_vol, cache_dir, mode="rw")
        proxy.with_volume_mapping(socket_vol, "/www/run/", mode="rw")
        proxy.with_volume_mapping(
            f"{cls.config.project_dir / 'proxy' / 'nginx.conf'}",
            "/etc/nginx/nginx.conf"
        )

        proxy.with_bind_ports(80, 8000)

        api.with_env("CURRENCY_LOCAL_DIR", cache_dir)

        cls.api = api.start()
        cls.proxy = proxy.start()

        cls.ping_app_until_ready()

    @classmethod
    def tearDownClass(cls):
        cls.api.stop()
        cls.proxy.stop()
        cls.cleanup()

    @classmethod
    def base_url(cls):
        return f"http://{cls.proxy.get_container_host_ip()}:{list(cls.proxy.ports.values())[0]}"

    @classmethod
    def ping_app_until_ready(cls):
        for _ in range(10):
            with httpx.Client() as client, contextlib.suppress(httpx.ConnectError, httpx.RemoteProtocolError):
                response = client.get(f"{cls.base_url()}/sorts")
                if response.status_code == 200:
                    break
            time.sleep(2)

    def test_sorts_handle_get(self):
        with httpx.Client() as client:
            response = client.get(f"{self.base_url()}/sorts")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("algorithms", data)
        self.assertIsInstance(data["algorithms"], list)
        self.assertTrue(len(data["algorithms"]) > 0)

    def test_sorts_handle_post(self):
        with httpx.Client() as client:
            response = client.post(f"{self.base_url()}/sorts")  # type: ignore
            self.assertEqual(405, response.status_code)  # cut on proxy
            self.assertEqual("GET", response.headers["Allow"])

    def test_caching_get(self):
        with httpx.Client() as client:
            # the first request was on startup
            response = client.get(f"{self.base_url()}/sorts")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers.get("X-Cache"), "HIT")

    def test_caching_post(self):
        with httpx.Client() as client:
            payload = {
                "sorting_type": "cheapest",
                "itineraries": [
                    {
                        "id": "urban_heritage_odyssey",
                        "duration_minutes": 275,
                        "price": {
                            "amount": "620",
                            "currency": "USD"
                        }
                    },
                ]
            }
            response = client.post(
                f"{self.base_url()}/sort_itineraries",
                json=payload
            )
            self.assertEqual(response.status_code, 200, response.content)
            self.assertEqual(response.headers.get("X-Cache"), "MISS")
            data1 = response.json()

            response = client.post(
                f"{self.base_url()}/sort_itineraries",
                json=payload
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers.get("X-Cache"), "HIT")
            data2 = response.json()

            self.assertEqual(data1, data2)
