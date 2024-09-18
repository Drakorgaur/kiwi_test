from unittest import mock

with mock.patch("environ.to_config") as mock_to_config:
    # mock cache as it is sys-dependent
    mock.patch("diskcache.Cache", mock.MagicMock()).start()

