Important Formatting Rules for Values:

- The column names in the database use lowercase underscore format, like `product_segment`, `ucp_final`, etc.
- However, the values inside columns (like 'Channel A', 'Group 1', 'Mainline Analog' etc.) should appear exactly as they are shown in the Excel — with spaces.
- DO NOT convert values like 'Channel A' to 'Channel_A' or 'Group 1' to 'Group_1'.
- Values inside `IN (...)` or `=` clauses must remain as original text.
