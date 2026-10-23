"""Mock 必须产出合法契约对象，否则它就不是个合格的替身。"""

from __future__ import annotations

from catvision_contracts import CatFaceModule, EarNotchModule, validate

from mocks import MockCameraSource, MockCatFaceModule, MockEarNotchModule, make_packet
from tests.factories import sample_frame_packet


def test_mocks_satisfy_protocols() -> None:
    assert isinstance(MockCatFaceModule(), CatFaceModule)
    assert isinstance(MockEarNotchModule(), EarNotchModule)


def test_mock_pipeline_objects_are_valid() -> None:
    packet = sample_frame_packet()
    faces = MockCatFaceModule().analyze(packet)
    assert faces, "Mock 至少要给一张脸"
    for f in faces:
        validate("cat_face", f)

    ears = MockEarNotchModule().analyze(packet, faces)
    assert len(ears) == len(faces), "EarNotch 必须和 CatFace 一一对应"
    for e in ears:
        validate("ear_notch", e)
    assert [e.track_id for e in ears] == [f.track_id for f in faces]


def test_mock_camera_makes_real_file(tmp_path) -> None:
    from modules.camera.frame_writer import FrameWriter

    src = MockCameraSource()
    data, sha1 = src.read(seq=0)
    assert len(data) > 1000

    w = FrameWriter(tmp_path, camera_id="cam-mock")
    from io import BytesIO

    from PIL import Image

    path, written_sha1 = w.write(Image.open(BytesIO(data)), seq=0)
    assert path.exists() and written_sha1


def test_make_packet_is_valid() -> None:
    validate("frame_packet", make_packet(seq=3))
