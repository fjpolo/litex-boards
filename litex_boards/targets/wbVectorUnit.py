from migen import *
from litex.soc.interconnect.csr import *
from litex.soc.interconnect.wishbone import Interface

class wbVectorUnit(Module, AutoCSR):
    def __init__(self, data_width=32):
        # Wishbone interfaces
        self.master_bus = Interface(data_width=data_width)
        self.slave_bus = Interface(data_width=data_width, address_width=3)
        
        # CSR registers
        self.control = CSRStorage(2)  # 2-bit control command
        self.mem_base_addr = CSRStorage(32)
        self.num_elements = CSRStorage(32)
        self.status = CSRStatus(2)    # Read-only status
        self.irq_status = CSRStatus(1) # Read-only interrupt status
        
        # Internal signals
        self.control_cmd = Signal(2)
        self.mem_base_addr_s = Signal(32)
        self.num_elements_s = Signal(32)
        self.status_s = Signal(2)
        self.irq = Signal()
        
        # Connect CSR to internal logic
        self.comb += [
            self.control_cmd.eq(self.control.storage),
            self.mem_base_addr_s.eq(self.mem_base_addr.storage),
            self.num_elements_s.eq(self.num_elements.storage),
            self.status.status.eq(self.status_s),
            self.irq_status.status.eq(self.irq)
        ]
        
        # Add Verilog source
        self.specials += Instance("wbVectorUnit",
            ("p_DATA_WIDTH", data_width),
            ("i_clk", ClockSignal()),
            ("i_rst", ResetSignal()),
            ("i_control_cmd", self.control_cmd),
            ("i_mem_base_addr", self.mem_base_addr_s),
            ("i_num_elements", self.num_elements_s),
            ("o_status", self.status_s),
            ("irq_o", self.irq),
            # Wishbone master connections
            ("wb_m_cyc_o", self.master_bus.cyc),
            ("wb_m_stb_o", self.master_bus.stb),
            ("wb_m_we_o", self.master_bus.we),
            ("wb_m_adr_o", self.master_bus.adr),
            ("wb_m_dat_w_o", self.master_bus.dat_w),
            ("wb_m_sel_o", self.master_bus.sel),
            ("wb_m_ack_i", self.master_bus.ack),
            ("wb_m_dat_r_i", self.master_bus.dat_r),
            ("wb_m_err_i", self.master_bus.err)
        )