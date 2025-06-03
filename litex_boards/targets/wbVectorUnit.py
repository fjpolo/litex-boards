# File: ~/Workspace/wbVectorUnit/litex/litex-boards/litex_boards/targets/wbVectorUnit.py
from migen import *
from litex.gen import *
from litex.soc.interconnect import wishbone

class wbVectorUnit(LiteXModule):
    def __init__(self, data_width=32):
        self.data_width = data_width

        # Wishbone MASTER Interface (for Vector Unit to initiate memory access)
        # Note: This was previously removed, but your provided file included it again.
        # Ensure this is commented out or removed in sipeed_tang_nano_20k.py if not in use.
        self.master_bus = wishbone.Interface(data_width=data_width, address_width=32)

        # Wishbone SLAVE Interface (for CPU to access Vector Unit's registers)
        self.slave_bus = wishbone.Interface(data_width=data_width, address_width=8)

        # ----------------------------------------------------------------------
        # Internal Registers of the Vector Unit (exposed via Wishbone Slave)
        # ----------------------------------------------------------------------
        self.status_reg             = Signal(data_width, reset=0)
        self.control_register       = Signal(data_width, reset=0)
        self.address_register       = Signal(data_width, reset=0)
        self.element_count_register = Signal(data_width, reset=0)
        self.counter_register       = Signal(data_width, reset=0xFFFFF000)

        # Registered signals for Wishbone slave outputs (driven by FSM in sync domain)
        o_ack   = Signal()
        o_dat_r = Signal(data_width, reset=0x12345678)
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

        # !!! CORE CHANGE: Continuous increment for counter_register !!!
        # This occurs on every rising edge of the system clock.
        self.sync += self.counter_register.eq(self.counter_register + 1)

        # Define internal FSM states
        fsm.act("IDLE",
            o_ack.eq(0), # Keep ack low by default
            o_err.eq(0), # Keep err low by default

            # Outer If statement: Check for valid request
            If(self.slave_bus.cyc & self.slave_bus.stb,
                # Actions if request is valid (grouped in a list if multiple)
                [
                    # Inner If statement: Check for Read or Write
                    If(~self.slave_bus.we, # Read transaction
                        # Actions for Read (grouped in a list if multiple)
                        [
                            Case(self.slave_bus.adr, {
                                0b000: NextValue(o_dat_r, self.status_reg),
                                0b001: NextValue(o_dat_r, self.control_register),
                                0b010: NextValue(o_dat_r, self.address_register),
                                0b011: NextValue(o_dat_r, self.element_count_register),
                                0b100: NextValue(o_dat_r, self.counter_register),
                                "default": NextValue(o_dat_r, 0xDEADFE05) # Return 0 for unmapped reads
                            })
                        ]
                    ).Else( # Write transaction
                        # Actions for Write (grouped in a list if multiple)
                        [
                            Case(self.slave_bus.adr, {
                                0b000: NextValue(self.status_reg,             self.slave_bus.dat_w),
                                0b001: NextValue(self.control_register,       self.slave_bus.dat_w),
                                0b010: NextValue(self.address_register,       self.slave_bus.dat_w),
                                0b011: NextValue(self.element_count_register, self.slave_bus.dat_w),
                                # !!! REMOVED WRITE ACCESS FOR counter_register !!!
                                # 0b100: NextValue(self.counter_register,       self.slave_bus.dat_w),
                            }),
                            NextValue(o_dat_r, 0) # For writes, clear data output (or provide read data if needed)
                        ]
                    ),
                    NextState("ACK_STATE") # Transition to ACK_STATE after processing request
                ]
            ).Else( # No request
                # Actions if no request (grouped in a list if multiple)
                [
                    NextState("IDLE") # Stay in IDLE state
                ]
            )
        )

        fsm.act("ACK_STATE",
            o_ack.eq(1), # Assert ACK in this cycle
            o_err.eq(0), # No error
            NextState("IDLE") # Return to IDLE to await next transaction
        )