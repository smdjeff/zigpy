from unittest import mock

import zigpy.device
import zigpy.endpoint
import zigpy.quirks
from zigpy.zcl import Cluster

ALLOWED_SIGNATURE = set([
    'device_type',
    'input_clusters',
    'output_clusters',
    'profile_id',
])
ALLOWED_REPLACEMENT = set([
    'device_type',
    'endpoints',
    'profile_id',
])


def test_registry():
    class TestDevice(zigpy.quirks.CustomDevice):
        signature = {}

    assert TestDevice in zigpy.quirks._DEVICE_REGISTRY
    assert zigpy.quirks._DEVICE_REGISTRY.pop() == TestDevice  # :-/


def test_get_device():
    application = mock.sentinel.application
    ieee = mock.sentinel.ieee
    nwk = mock.sentinel.nwk
    real_device = zigpy.device.Device(application, ieee, nwk)

    real_device.add_endpoint(1)
    real_device[1].profile_id = 255
    real_device[1].device_type = 255
    real_device[1].add_input_cluster(3)
    real_device[1].add_output_cluster(6)

    class TestDevice:
        signature = {
        }

        def __init__(*args, **kwargs):
            pass

    registry = [TestDevice]

    get_device = zigpy.quirks.get_device

    assert get_device(real_device, registry) is real_device

    TestDevice.signature[1] = {'profile_id': 1}
    assert get_device(real_device, registry) is real_device

    TestDevice.signature[1]['profile_id'] = 255
    TestDevice.signature[1]['device_type'] = 1
    assert get_device(real_device, registry) is real_device

    TestDevice.signature[1]['device_type'] = 255
    assert get_device(real_device, registry) is real_device

    TestDevice.signature[1]['input_clusters'] = [3]
    assert get_device(real_device, registry) is real_device

    TestDevice.signature[1]['output_clusters'] = [6]
    assert isinstance(get_device(real_device, registry), TestDevice)


def test_custom_devices():
    # Validate that all CustomDevices look sane
    for device in zigpy.quirks._DEVICE_REGISTRY:
        # Check that the signature data is OK
        for profile_id, profile_data in device.signature.items():
            assert isinstance(profile_id, int)
            assert set(profile_data.keys()) - ALLOWED_SIGNATURE == set()

        # Check that the replacement data is OK
        assert set(device.replacement.keys()) - ALLOWED_REPLACEMENT == set()
        for epid, epdata in device.replacement.get('endpoints', {}).items():
            assert (epid in device.signature) or (
                'profile' in epdata and 'device_type' in epdata)
            if 'profile' in epdata:
                profile = epdata['profile']
                assert isinstance(profile, int) and 0 <= profile <= 0xffff
            if 'device_type' in epdata:
                device_type = epdata['device_type']
                assert isinstance(device_type, int) and 0 <= device_type <= 0xffff

            all_clusters = (epdata.get('input_clusters', []) +
                            epdata.get('output_clusters', []))
            for cluster in all_clusters:
                assert (
                    (isinstance(cluster, int) and cluster in Cluster._registry) or
                    issubclass(cluster, Cluster)
                )


def test_custom_device():
    class Device(zigpy.quirks.CustomDevice):
        signature = {}

        class MyEndpoint:
            def __init__(self, device, endpoint_id, *args, **kwargs):
                assert args == (mock.sentinel.custom_endpoint_arg, replaces)

        class MyCluster(zigpy.quirks.CustomCluster):
            cluster_id = 0x8888

        replacement = {
            'endpoints': {
                1: {
                    'profile_id': mock.sentinel.profile_id,
                    'input_clusters': [0x0000, MyCluster],
                    'output_clusters': [0x0001, MyCluster],
                },
                2: (MyEndpoint, mock.sentinel.custom_endpoint_arg),
            }
        }

    assert 0x8888 not in Cluster._registry

    replaces = mock.MagicMock()
    replaces[1].device_type = mock.sentinel.device_type
    test_device = Device(None, None, None, replaces)
    assert test_device[1].profile_id == mock.sentinel.profile_id
    assert test_device[1].device_type == mock.sentinel.device_type

    assert 0x0000 in test_device[1].in_clusters
    assert 0x8888 in test_device[1].in_clusters
    assert isinstance(test_device[1].in_clusters[0x8888], Device.MyCluster)

    assert 0x0001 in test_device[1].out_clusters
    assert 0x8888 in test_device[1].out_clusters
    assert isinstance(test_device[1].out_clusters[0x8888], Device.MyCluster)

    assert isinstance(test_device[2], Device.MyEndpoint)

    test_device.add_endpoint(3)
    assert isinstance(test_device[3], zigpy.endpoint.Endpoint)

    assert zigpy.quirks._DEVICE_REGISTRY.pop() == Device  # :-/
