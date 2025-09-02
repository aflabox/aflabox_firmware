from pydantic import BaseModel, ConfigDict, conlist
from typing import Optional, List, Tuple
from datetime import datetime
from enum import Enum
import uuid

# Corrected for Pydantic v2
TwoFloats = conlist(float, min_length=2, max_length=2)
NineFloats = conlist(float, min_length=9, max_length=9)
FourInts = conlist(int, min_length=4, max_length=4)
TwoInts = conlist(int, min_length=2, max_length=2)

class ImageType(str, Enum):
    RAW = 'Raw'
    DNG = 'DNG'
    RGB = 'RGB'
    JPG = 'JPG'

class LightType(str, Enum):
    UV_365 = 'UV_365'
    UV_395 = 'UV_365'
    WHITE = 'White'

class TimestampSettings(BaseModel):
    SensorTimestamp: Optional[int] = None
    FrameDuration: Optional[int] = None
    ExposureTime: Optional[int] = None
    DigitalGain: Optional[float] = None
    AnalogueGain: Optional[float] = None
    SensorSensitivity: Optional[float] = None

class FocusExposure(BaseModel):
    AfState: Optional[int] = None
    AfPauseState: Optional[int] = None
    AeLocked: Optional[bool] = None
    FocusFoM: Optional[int] = None
    LensPosition: Optional[float] = None

class ImageQuality(BaseModel):
    ColourGains: Optional[TwoFloats] = None  # R and B gains (2 floats)
    ColourTemperature: Optional[int] = None
    Lux: Optional[float] = None
    ColourCorrectionMatrix: Optional[NineFloats] = None  # 3x3 matrix

class SensorDetails(BaseModel):
    SensorTemperature: Optional[float] = None
    SensorMode: Optional[int] = None
    SensorBlackLevels: Optional[FourInts] = None

class CameraProperties(BaseModel):
    Model: Optional[str] = None
    UnitCellSize: Optional[TwoFloats] = None
    Location: Optional[Tuple[float, float, float]] = None  # Adjusted to (x, y, z)
    Rotation: Optional[float] = None
    PixelArraySize: Optional[TwoFloats] = None
    PixelArrayActiveAreas: Optional[List[FourInts]] = None
    ColorFilterArrangement: Optional[str] = None  # Changed to str (more realistic for filter name)
    ScalerCropMaximum: Optional[FourInts] = None
    SystemDevices: Optional[List[str]] = None  # Typically device paths like `/dev/video0`

class CapturedImage(BaseModel):
    guid: uuid.UUID
    light_type: LightType
    image_type: ImageType
    path: str
    focus_exposure_metadata: Optional[FocusExposure] = None
    sensor_details: Optional[SensorDetails] = None
    image_quality_metadata: Optional[ImageQuality] = None
    camera_properties: Optional[CameraProperties] = None

class TestSample(BaseModel):
    guid: uuid.UUID
    detected_crop: Optional[str] = None
    images: List[CapturedImage]

class CropTest(BaseModel):
    guid: uuid.UUID
    device_id: int
    reference: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    test_date: datetime
    tests: List[TestSample]

# Function to initialize
def initialize_empty_test(device_id, ref=None) -> Tuple[CropTest, TestSample]:
    from utils.helpers import generate_reference, now

    ref = generate_reference(5) if ref is None else ref
    ref = f"{ref}{device_id}"

    crop_test = CropTest(
        device_id=device_id,
        guid=uuid.uuid4(),
        reference=ref,
        test_date=now(),
        tests=[]
    )

    sample = TestSample(
        guid=uuid.uuid4(),
        detected_crop=None,
        images=[]
    )

    return crop_test, sample
