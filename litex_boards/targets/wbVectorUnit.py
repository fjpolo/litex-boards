# File: ~/Workspace/wbVectorUnit/litex/litex-boards/litex_boards/targets/wbVectorUnit.py
from migen import *
from litex.gen import *
from litex.soc.interconnect import wishbone

class WBVectorUnit(LiteXModule):
    def __init__(self, data_width=32):
        self.data_width = data_width

        # Wishbone MASTER Interface (for Vector Unit to initiate memory access)
        self.master_bus = wishbone.Interface(data_width=data_width, address_width=32)

        # Wishbone SLAVE Interface (for CPU to access Vector Unit's registers)
        self.slave_bus = wishbone.Interface(data_width=data_width, address_width=3)

        # Registered signals for Wishbone slave outputs (driven by FSM in sync domain)
        o_ack   = Signal()
        o_dat_r = Signal(data_width, reset=0x12345678) # <--- NEW DISTINCT RESET VALUE
        o_err   = Signal()

        # Connect registered outputs to the actual bus ports
        self.comb += [
            self.slave_bus.ack.eq(o_ack),
            self.slave_bus.dat_r.eq(o_dat_r),
            self.slave_bus.err.eq(o_err)
        ]

        # FSM for Pipelined Wishbone B4 Slave
        fsm = FSM(reset_state="IDLE")
        self.submodules += fsm

        # Define internal FSM states
        fsm.act("IDLE",
            o_ack.eq(0), # Keep ack low by default
            o_err.eq(0), # Keep err low by default

            If(self.slave_bus.cyc & self.slave_bus.stb, # Valid request received
                # If read transaction, prepare data for the NEXT cycle
                If(~self.slave_bus.we,
                    NextValue(o_dat_r, 0xDEADBEEF) # Schedule data to be present next cycle
                ).Else(
                    # For writes, clear data output (or assign write data if relevant)
                    NextValue(o_dat_r, 0)
                ),
                NextState("ACK_STATE") # Move to state to assert ACK
            )
            # If no request, o_dat_r will retain its last value or default to reset (0x12345678)
        )

        fsm.act("ACK_STATE",
            o_ack.eq(1), # Assert ACK in this cycle
            o_err.eq(0), # No error
            # o_dat_r retains the value set in the previous IDLE state by NextValue
            NextState("IDLE") # Return to IDLE to await next transaction
        )