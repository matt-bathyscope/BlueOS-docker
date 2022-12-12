import pathlib

import pytest

from exceptions import InvalidFirmwareFile
from firmware.FirmwareDownload import FirmwareDownloader
from firmware.FirmwareInstall import FirmwareInstaller, get_supported_elf_archs
from typedefs import FlightController, Platform, Vehicle


@pytest.fixture(scope="module")
def downloader():
    downloader = FirmwareDownloader()
    downloader.download_manifest()
    yield downloader


def test_firmware_validation(downloader) -> None:
    installer = FirmwareInstaller()

    # Pixhawk1 and Pixhawk4 APJ firmwares should always work
    temporary_file = downloader.download(Vehicle.Sub, Platform.Pixhawk1)
    installer.validate_firmware(temporary_file, Platform.Pixhawk1)

    temporary_file = downloader.download(Vehicle.Sub, Platform.Pixhawk4)
    installer.validate_firmware(temporary_file, Platform.Pixhawk4)


class TestELFPlatformSupport():
    def test_aarch64_support(self) -> None:
        archs = get_supported_elf_archs("aarch64")
        assert len(archs) == 2
        assert "AArch64" in archs
        assert "ARM" in archs

    def test_armv7l_support(self) -> None:
        archs = get_supported_elf_archs("armv7l")
        assert len(archs) == 1
        assert "ARM" in archs

    def test_x86_64_support(self) -> None:
        archs = get_supported_elf_archs("x86_64")
        assert len(archs) == 1
        assert "x64" in archs

    def test_unsupported_arch(self) -> None:
        archs = get_supported_elf_archs("riscv64")
        assert len(archs) == 0

    def test_arm_validation(self, mocker, downloader) -> None:
        """Validates an ARM ELF binary installs on the intended architectures"""
        installer = FirmwareInstaller()
        sub_arm = downloader.download(Vehicle.Sub, Platform.Navigator)

        # the ARM binary should work on armv7l
        mocker.patch("platform.machine", return_value="armv7l")
        installer.validate_firmware(sub_arm, Platform.Navigator)
        board = FlightController(
            name="Navigator", manufacturer="Blue Robotics", platform=Platform.Navigator, path=None
        )
        installer.install_firmware(sub_arm, board, pathlib.Path(f"{sub_arm}_dest"))
        mocker.resetall()

        # the ARM binary should work on aarch64
        mocker.patch("platform.machine", return_value="aarch64")
        installer.validate_firmware(sub_arm, Platform.Navigator)
        mocker.resetall()

        # the ARM binary should NOT work on x86_64
        mocker.patch("platform.machine", return_value="x86_64")
        with pytest.raises(InvalidFirmwareFile):
            installer.validate_firmware(sub_arm, Platform.Navigator)
        mocker.resetall()

    def test_x64_validation(self, mocker, downloader) -> None:
        """Validates an x64 ELF binary installs on the intended architectures"""
        installer = FirmwareInstaller()
        sub_sitl_x64 = downloader.download(Vehicle.Sub, Platform.SITL, version="DEV")

        # the x64 binary should work on x86_64
        mocker.patch("platform.machine", return_value="x86_64")
        installer.validate_firmware(sub_sitl_x64, Platform.Navigator)
        board = FlightController(
            name="SITL", manufacturer="ArduPilot Team", platform=Platform.SITL, path=None
        )
        installer.install_firmware(sub_sitl_x64, board, pathlib.Path(f"{sub_sitl_x64}_dest"))
        mocker.resetall()

        # the x64 binary should NOT work on armv7l
        mocker.patch("platform.machine", return_value="armv7l")
        with pytest.raises(InvalidFirmwareFile):
            installer.validate_firmware(sub_sitl_x64, Platform.Navigator)
        mocker.resetall()

        # the x64 binary should NOT work on aarch64
        mocker.patch("platform.machine", return_value="aarch64")
        with pytest.raises(InvalidFirmwareFile):
            installer.validate_firmware(sub_sitl_x64, Platform.Navigator)
        mocker.resetall()
