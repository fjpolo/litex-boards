from migen import *
from litex.soc.interconnect.wishbone import Interface

# This class acts as a simple wrapper for your Verilog module.
# It does NOT inherit from LiteX's Module or AutoCSR, as its registers are
# handled directly by the Verilog Wishbone slave.
class wbVectorUnit:
    def __init__(self, data_width=32):
        self.data_width = data_width

        # Wishbone MASTER Interface (for Vector Unit to initiate memory access)
        self.master_bus = Interface(data_width=data_width, address_width=32)

        # Wishbone SLAVE Interface (for CPU to access Vector Unit's registers)
        # The address_width is 3 because we have 32-bit registers, and each 32-bit word
        # takes 4 bytes. An address width of 3 allows for 2^3 = 8 words (0x00 to 0x1C).
        self.slave_bus = Interface(data_width=data_width, address_width=3)

        # Any direct signals you want to expose from the Verilog module to the Python/Migen side
        self.o_status_from_verilog = Signal(data_width) # Example output from Verilog

        # --- Instantiate the Verilog module and connect its ports ---
        # The 'specials' attribute is part of Migen's way to include HDL instances.
        self.specials = [
            Instance("wbVectorUnit",
                # Parameters
                ("p_DATA_WIDTH", data_width),

                # Clock/Reset
                ("i_clk",        ClockSignal()),
                ("i_rst",        ResetSignal()),

                # Wishbone SLAVE Ports (These connect to self.slave_bus defined above)
                ("wb_s_cyc_i",   self.slave_bus.cyc),
                ("wb_s_stb_i",   self.slave_bus.stb),
                ("wb_s_we_i",    self.slave_bus.we),
                ("wb_s_adr_i",   self.slave_bus.adr),
                ("wb_s_dat_w_i", self.slave_bus.dat_w),
                ("wb_s_sel_i",   self.slave_bus.sel),
                ("wb_s_ack_o",   self.slave_bus.ack),
                ("wb_s_dat_r_o", self.slave_bus.dat_r),
                ("wb_s_err_o",   self.slave_bus.err),

                # Wishbone MASTER Ports (These connect to self.master_bus defined above)
                ("wb_m_cyc_o", self.master_bus.cyc),
                ("wb_m_stb_o", self.master_bus.stb),
                ("wb_m_we_o",  self.master_bus.we),
                ("wb_m_adr_o", self.master_bus.adr),
                ("wb_m_dat_w_o", self.master_bus.dat_w),
                ("wb_m_sel_o", self.master_bus.sel),
                ("wb_m_ack_i", self.master_bus.ack),
                ("wb_m_dat_r_i", self.master_bus.dat_r),
                ("wb_m_err_i", self.master_bus.err),

                # Other direct I/O to/from the Verilog module
                ("o_status",     self.o_status_from_verilog), # Example connection
            )
        ]