# wbDualPortBRAM_migen.py
from migen import *
from litex.soc.interconnect.wishbone import Interface

class WBDualPortBRAM(Module):
    """
    A Wishbone B4 Pipelined Slave for a Dual-Port Block RAM, written in Migen.
    """
    def __init__(self, addr_width=10, data_width=32):
        self.addr_width = addr_width
        self.data_width = data_width
        self.mem_size = 2**addr_width # Total number of words in RAM

        self.bus = Interface(data_width=data_width, address_width=addr_width)
        self.mem = Array([Signal(data_width) for _ in range(self.mem_size)])

        # Declare the internal registered Wishbone inputs
        # These are Signals (hardware wires/registers)
        adr_reg   = Signal(addr_width, name="adr_reg")
        dat_w_reg = Signal(data_width, name="dat_w_reg")
        sel_reg   = Signal(data_width // 8, name="sel_reg")
        we_reg    = Signal(name="we_reg")
        stb_reg   = Signal(name="stb_reg")
        cyc_reg   = Signal(name="cyc_reg")

        # Declare a temporary combinatorial signal for the byte-enabled data to be written.
        # This signal will hold the data that *would* be written, after considering byte enables.
        # It's a combinatorial signal, so it doesn't need to be part of self.sync.
        dat_w_byte_enabled = Signal(data_width, name="dat_w_byte_enabled")

        # --- Combinatorial Logic for 'dat_w_byte_enabled' ---
        # 1. Default 'dat_w_byte_enabled' to the current content of the memory location.
        #    This is important for byte-enable logic, as bytes not enabled should retain their old value.
        self.comb += dat_w_byte_enabled.eq(self.mem[adr_reg])
        self.comb += self.bus.err.eq(0) # Also keep this default combinatorial


        # 2. Apply byte enables combinatorially to 'dat_w_byte_enabled'.
        #    This Python loop *generates* Migen 'If' statements. Each 'If' statement
        #    is then added to the 'self.comb' domain.
        for i in range(data_width // 8):
            byte_slice = slice(i * 8, (i + 1) * 8)
            # If the byte enable (sel_reg[i]) is active, update the corresponding byte slice
            # of 'dat_w_byte_enabled' with the incoming write data byte.
            self.comb += If(sel_reg[i],
                dat_w_byte_enabled[byte_slice].eq(dat_w_reg[byte_slice])
            )


        # --- Synchronous Logic (at positive edge of the clock) ---
        self.sync += [
            # Default outputs for the current cycle
            self.bus.ack.eq(0),
            self.bus.dat_r.eq(0),

            # Stage 1: Register Wishbone inputs for pipelining (B4 protocol)
            # These assignments happen at the positive clock edge.
            adr_reg   .eq(self.bus.adr),
            dat_w_reg .eq(self.bus.dat_w),
            sel_reg   .eq(self.bus.sel),
            we_reg    .eq(self.bus.we),
            stb_reg   .eq(self.bus.stb),
            cyc_reg   .eq(self.bus.cyc),

            # Stage 2: Handle Wishbone transaction based on registered inputs
            # This 'If' block encapsulates the logic for a Wishbone transaction.
            If(stb_reg & cyc_reg,
                self.bus.ack.eq(1), # Assert ACK for the transaction from the previous cycle

                If(we_reg,
                    # If write enable is high, synchronously write the fully
                    # byte-enabled data (dat_w_byte_enabled) to the memory.
                    self.mem[adr_reg].eq(dat_w_byte_enabled)
                ).Else(
                    # If write enable is low (read operation), output the data
                    # read from memory synchronously.
                    self.bus.dat_r.eq(self.mem[adr_reg])
                )
            )
        ]