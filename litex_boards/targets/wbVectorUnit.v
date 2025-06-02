// This is your Verilog module that implements the Wishbone slave
// and potentially a Wishbone master.
module wbVectorUnit #(
    parameter DATA_WIDTH = 32
)(
    input  wire                 i_clk,
    input  wire                 i_rst,

    // Wishbone SLAVE B4 Interface (CPU -> Vector Unit registers)
    input  wire                 wb_s_cyc_i,     // Cycle valid
    input  wire                 wb_s_stb_i,     // Strobe (address/data valid)
    input  wire                 wb_s_we_i,      // Write enable (1 for write, 0 for read)
    input  wire [31:0]          wb_s_adr_i,     // Address (byte address)
    input  wire [DATA_WIDTH-1:0] wb_s_dat_w_i,   // Write data
    input  wire [DATA_WIDTH/8-1:0] wb_s_sel_i,   // Byte select

    output wire                 wb_s_ack_o,     // Acknowledge
    output wire [DATA_WIDTH-1:0] wb_s_dat_r_o,   // Read data
    output wire                 wb_s_err_o,     // Error

    // Wishbone MASTER B4 Interface (Vector Unit -> Main Memory)
    output wire                 wb_m_cyc_o,     // Cycle valid
    output wire                 wb_m_stb_o,     // Strobe (address/data valid)
    output wire                 wb_m_we_o,      // Write enable
    output wire [31:0]          wb_m_adr_o,     // Address
    output wire [DATA_WIDTH-1:0] wb_m_dat_w_o,   // Write data
    output wire [DATA_WIDTH/8-1:0] wb_m_sel_o,   // Byte select

    input  wire                 wb_m_ack_i,     // Acknowledge
    input  wire [DATA_WIDTH-1:0] wb_m_dat_r_i,   // Read data
    input  wire                 wb_m_err_i,     // Error

    // Example direct output (if you still want this exposed)
    output wire [31:0]          o_status
);

    // Internal registers of the Vector Unit.
    // They will only be reset to 0, not updated by writes for this diagnostic.
    reg [DATA_WIDTH-1:0] status_reg;
    reg [DATA_WIDTH-1:0] control_reg;
    reg [DATA_WIDTH-1:0] address_reg;

    // Default outputs for Wishbone Master (unless actively driven)
    assign wb_m_cyc_o   = 1'b0;
    assign wb_m_stb_o   = 1'b0;
    assign wb_m_we_o    = 1'b0;
    assign wb_m_adr_o   = 32'd0;
    assign wb_m_dat_w_o = 32'd0;
    assign wb_m_sel_o   = 4'b1111;

    // -------------------------------------------------------------------------
    // Wishbone SLAVE B4 Pipelined Logic
    // -------------------------------------------------------------------------

    // State definitions for the simple FSM
    localparam IDLE = 2'b00;
    localparam ACK_PULSE = 2'b01; // State to generate ACK and read data

    // State register
    reg [1:0] current_state, next_state;

    // Registered outputs for pipelined behavior
    reg wb_s_ack_o_q;
    reg [DATA_WIDTH-1:0] wb_s_dat_r_o_q;
    reg wb_s_err_o_q;

    // Connect registered outputs to actual ports
    assign wb_s_ack_o = wb_s_ack_o_q;
    assign wb_s_dat_r_o = wb_s_dat_r_o_q;
    assign wb_s_err_o = wb_s_err_o_q; // Still 0 for this test

    // Main FSM for pipelined Wishbone slave
    always @(posedge i_clk or posedge i_rst) begin
        if (i_rst) begin
            current_state <= IDLE;
            wb_s_ack_o_q <= 1'b0;
            wb_s_dat_r_o_q <= {DATA_WIDTH{1'b0}};
            wb_s_err_o_q <= 1'b0;
        end else begin
            current_state <= next_state;

            // Default values for outputs in the current cycle before state logic
            wb_s_ack_o_q <= 1'b0;
            wb_s_err_o_q <= 1'b0;
            // IMPORTANT: For read data, we only update it when we transition to ACK_PULSE
            // otherwise, it should hold the previous data or go to 0.
            // For this specific diagnostic, we keep it simple: only drive when expected.

            case (current_state)
                IDLE: begin
                    if (wb_s_cyc_i & wb_s_stb_i) begin // Valid request received
                        // If it's a read request, prepare data for the *next* cycle
                        if (!wb_s_we_i) begin
                            // Hardcode the read data here for the diagnostic test
                            wb_s_dat_r_o_q <= 32'hDEADBEEF;
                        end
                        // No write logic: internal registers are not updated by writes
                        next_state <= ACK_PULSE; // Transition to state where ACK will be asserted
                    end else begin
                        next_state <= IDLE;
                    end
                end
                ACK_PULSE: begin
                    // In this state, assert ACK for the previous request
                    wb_s_ack_o_q <= 1'b1;
                    // The read data (wb_s_dat_r_o_q) was already latched in the IDLE state if it was a read.
                    // Transition back to IDLE to be ready for the next request.
                    next_state <= IDLE;
                end
                default: next_state <= IDLE; // Should not happen, but safe fallback
            endcase
        end
    end

    // Internal Register storage (only reset to 0, no writes from Wishbone)
    always @(posedge i_clk or posedge i_rst) begin
        if (i_rst) begin
            status_reg  <= {DATA_WIDTH{1'b0}};
            control_reg <= {DATA_WIDTH{1'b0}};
            address_reg <= {DATA_WIDTH{1'b0}};
        end
        // No write logic here for this diagnostic: registers will not change from their reset values.
    end

    // Example direct output - will always be 0 after reset, as no writes happen
    assign o_status = status_reg;

endmodule
