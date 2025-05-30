#!/usr/bin/env python3

#
# This file is part of LiteX-Boards.
#
# Copyright (c) 2022 Icenowy Zheng <icenowy@aosc.io>
# Copyright (c) 2022 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.gen import *

from litex.build.io import DDROutput

from litex.soc.cores.clock.gowin_gw2a import GW2APLL
from litex.soc.integration.soc_core import *
from litex.soc.integration.soc import SoCRegion
from litex.soc.integration.builder import *
from litex.soc.cores.gpio import GPIOIn
from litex.soc.cores.led import LedChaser, WS2812
from litex.soc.cores.video import VideoGowinHDMIPHY

from litedram.modules import M12L64322A # FIXME: use the real model number
from litedram.phy import GENSDRPHY

from litex_boards.platforms import sipeed_tang_nano_20k

from wbDualPortBRAM_migen import WBDualPortBRAM
# import os
# import math
# import sys # Used for sys.exit(1)
# from litex.soc.integration.common import get_mem_data

# CRG ----------------------------------------------------------------------------------------------

class _CRG(LiteXModule):
    def __init__(self, platform, sys_clk_freq, with_hdmi=False):
        self.rst = Signal()
        self.cd_sys  = ClockDomain()
        self.cd_por  = ClockDomain()
        if with_hdmi:
            self.cd_hdmi  = ClockDomain()
            self.cd_hdmi5x = ClockDomain()

        # Clk
        clk27 = platform.request("clk27")

        # Power on reset
        por_count = Signal(16, reset=2**16-1)
        por_done = Signal()
        self.comb += self.cd_por.clk.eq(clk27)
        self.comb += por_done.eq(por_count == 0)
        self.sync.por += If(~por_done, por_count.eq(por_count - 1))

        # PLL
        self.pll = pll = GW2APLL(devicename=platform.devicename, device=platform.device)
        self.comb += pll.reset.eq(~por_done)
        pll.register_clkin(clk27, 27e6)
        pll.create_clkout(self.cd_sys, sys_clk_freq)

        # HDMI PLL
        if with_hdmi:
            self.video_pll = video_pll = GW2APLL(devicename=platform.devicename, device=platform.device)
            video_pll.register_clkin(clk27, 27e6)
            video_pll.create_clkout(self.cd_hdmi5x, 125e6, margin=1e-2)
            self.specials += Instance("CLKDIV",
                p_DIV_MODE = "5",
                i_RESETN   = 1, # Disable reset signal.
                i_CALIB    = 0, # No calibration.
                i_HCLKIN   = self.cd_hdmi5x.clk,
                o_CLKOUT   = self.cd_hdmi.clk
            )

# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCCore):
    def __init__(self, toolchain="gowin", sys_clk_freq=48e6,
        with_led_chaser = True,
        with_rgb_led    = False,
        with_buttons    = True,
        with_spi_flash  = False,
        with_video_terminal  = False,
        with_video_colorbars = False,
        **kwargs):

        platform = sipeed_tang_nano_20k.Platform(toolchain=toolchain)

        with_hdmi = with_video_terminal or with_video_colorbars

        # CRG --------------------------------------------------------------------------------------
        self.crg = _CRG(platform, sys_clk_freq, with_hdmi=with_hdmi)

        # SoCCore ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, sys_clk_freq, ident="LiteX SoC on Tang Nano 20K", **kwargs)

        # SPI Flash: XT25F64B ----------------------------------------------------------------------
        if with_spi_flash:
            from litespi.modules import W25Q64 as SpiFlashModule # compatible with XT25F64B
            from litespi.opcodes import SpiNorFlashOpCodes as Codes
            self.add_spi_flash(mode="1x", module=SpiFlashModule(Codes.READ_1_1_1))

        # SDR SDRAM --------------------------------------------------------------------------------
        if not self.integrated_main_ram_size:
            class SDRAMPads:
                def __init__(self):
                    self.clk   = platform.request("O_sdram_clk")
                    self.cke   = platform.request("O_sdram_cke")
                    self.cs_n  = platform.request("O_sdram_cs_n")
                    self.cas_n = platform.request("O_sdram_cas_n")
                    self.ras_n = platform.request("O_sdram_ras_n")
                    self.we_n  = platform.request("O_sdram_wen_n")
                    self.dm    = platform.request("O_sdram_dqm")
                    self.a     = platform.request("O_sdram_addr")
                    self.ba    = platform.request("O_sdram_ba")
                    self.dq    = platform.request("IO_sdram_dq")
            sdram_pads = SDRAMPads()

            self.specials += DDROutput(0, 1, sdram_pads.clk, ClockSignal("sys"))

            self.sdrphy = GENSDRPHY(sdram_pads, sys_clk_freq)
            self.add_sdram("sdram",
                phy           = self.sdrphy,
                module        = M12L64322A(sys_clk_freq, "1:1"), # FIXME.
                l2_cache_size = 128,
            )

        # Video ------------------------------------------------------------------------------------
        if with_hdmi:
            self.videophy = VideoGowinHDMIPHY(platform.request("hdmi"), clock_domain="hdmi")
            if with_video_terminal:
                # self.add_video_terminal(phy=self.videophy, timings="800x600@60Hz", clock_domain="hdmi")
                self.add_video_terminal(phy=self.videophy, timings="640x480@60Hz", clock_domain="hdmi")
            if with_video_colorbars:
                self.add_video_colorbars(phy=self.videophy, timings="800x600@60Hz", clock_domain="hdmi")

        # Leds -------------------------------------------------------------------------------------
        if with_led_chaser:
            self.leds = LedChaser(
                pads         = platform.request_all("led_n"),
                sys_clk_freq = sys_clk_freq
            )

        # RGB Led ----------------------------------------------------------------------------------
        if with_rgb_led:
            self.rgb_led = WS2812(
                pad          = platform.request("rgb_led"),
                nleds        = 1,
                sys_clk_freq = sys_clk_freq
            )
            self.bus.add_slave(name="rgb_led", slave=self.rgb_led.bus, region=SoCRegion(
                origin = 0x2000_0000, # Keep this address for RGB LED
                size   = 4,
            ))

        # Buttons ----------------------------------------------------------------------------------
        if with_buttons:
            self.buttons = GPIOIn(pads=~platform.request_all("btn"))

        # DPBRAM -----------------------------------------------------------------------------------
        # Define parameters for your BRAM module
        BRAM_ADDR_WIDTH = 7 # 7 bits for 128 words (2**7 = 128)
        BRAM_DATA_WIDTH = 32 # 32 bits per word

        # Calculate memory size in bytes
        BRAM_SIZE_WORDS = (1 << BRAM_ADDR_WIDTH)
        BRAM_SIZE_BYTES = BRAM_SIZE_WORDS * (BRAM_DATA_WIDTH // 8) # 128 words * 4 bytes/word = 512 bytes

        # Define a base address for your custom BRAM (CHOOSE A NEW ADDRESS TO AVOID CONFLICTS!)
        # Using 0x3000_0000 to avoid conflict with RGB LED at 0x2000_0000
        CUSTOM_BRAM_BASE = 0x30000000 

        # 1. Instantiate your Migen BRAM module and keep a direct reference to it.
        #    This is the correct way to get the module instance *before* assigning it to submodules
        #    and then accessing its attributes.
        my_bram_instance = WBDualPortBRAM(addr_width=BRAM_ADDR_WIDTH, data_width=BRAM_DATA_WIDTH)

        # 2. Add the instance to the SoC's submodules.
        #    LiteX will discover this module for elaboration.
        self.submodules.my_bram_slave = my_bram_instance

        # 3. Add the Wishbone interface of your custom module as a slave to the SoC's main bus.
        #    Use the direct instance reference to get its .bus attribute.
        self.bus.add_slave(
            name="my_bram_slave",
            slave=my_bram_instance.bus,  # Use the direct instance reference
            # region=mem_regions.MemRegion(origin=CUSTOM_BRAM_BASE, size=BRAM_SIZE_BYTES)
            region=SoCRegion(origin=CUSTOM_BRAM_BASE, size=BRAM_SIZE_BYTES)
        )





        # # --- ROM Boot for demo.bin ---
        # Add a custom ROM block for your application at 0x20000000.
        # 2**15 = 32KB. This should be ample for most bare-metal demos.
        # The name "bootrom" here will correspond to the region name in linker.ld
        self.add_rom("bootrom", 0x20000000, 2**15, contents=get_mem_data("bootrom.bin", endianness="little"))

        # Set the CPU's boot address to this new ROM.
        # This ensures the CPU jumps to 0x20000000 on reset.
        self.add_constant("ROM_BOOT_ADDRESS", 0x20000000)





        # # # --- SPIFlash Boot for demo.bin ---
        # # # Define the memory-mapped base address of your SPI Flash.
        # # # Confirm this address from your BIOS startup messages or build/regions.ld
        # # SPIFLASH_MEMORY_BASE = 0x30000000 # Common default for Tang Nano 20K

        # # # This offset MUST match the --offset used with openFPGALoader in Step 2.
        # # # APPLICATION_FLASH_OFFSET = 0x40000 # 256kB
        # # # APPLICATION_FLASH_OFFSET = 0x800000 # 8MB
        # # APPLICATION_FLASH_OFFSET = 0x700000 # 7MB

        # # # Add a constant that the BIOS will use to jump to the application in flash at startup
        # # self.add_constant("FLASH_BOOT_ADDRESS", SPIFLASH_MEMORY_BASE + APPLICATION_FLASH_OFFSET)

# Build --------------------------------------------------------------------------------------------

def main():
    from litex.build.parser import LiteXArgumentParser
    parser = LiteXArgumentParser(platform=sipeed_tang_nano_20k.Platform, description="LiteX SoC on Tang Nano 20K.")
    parser.add_target_argument("--flash",        action="store_true",      help="Flash Bitstream.")
    parser.add_target_argument("--sys-clk-freq", default=48e6, type=float, help="System clock frequency.")
    parser.add_target_argument("--with-spi-flash", action="store_true", help="Enable SPI Flash (MMAPed).")
    parser.add_target_argument("--with-rbg-led", action="store_true", help="Enable WS2812 RGB Led.")
    sdopts = parser.target_group.add_mutually_exclusive_group()
    sdopts.add_argument("--with-spi-sdcard",            action="store_true", help="Enable SPI-mode SDCard support.")
    sdopts.add_argument("--with-sdcard",                action="store_true", help="Enable SDCard support.")
    viopts = parser.target_group.add_mutually_exclusive_group()
    viopts.add_argument("--with-video-terminal",   action="store_true", help="Enable Video Terminal (HDMI).")
    viopts.add_argument("--with-video-colorbars",  action="store_true", help="Enable Video Colorbars (HDMI).")
    args = parser.parse_args()

    soc = BaseSoC(
        toolchain    = args.toolchain,
        sys_clk_freq = args.sys_clk_freq,
        with_rgb_led         = args.with_rbg_led,
        with_spi_flash       = args.with_spi_flash,
        with_video_terminal  = args.with_video_terminal,
        with_video_colorbars = args.with_video_colorbars,
        **parser.soc_argdict
    )
    if args.with_spi_sdcard:
        soc.add_spi_sdcard()
    if args.with_sdcard:
        soc.add_sdcard()

    builder = Builder(soc, **parser.builder_argdict)
    if args.build:
        builder.build(**parser.toolchain_argdict)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(builder.get_bitstream_filename(mode="sram"))

    if args.flash:
        prog = soc.platform.create_programmer()
        prog.flash(0, builder.get_bitstream_filename(mode="flash", ext=".fs"), external=True)

if __name__ == "__main__":
    main()
