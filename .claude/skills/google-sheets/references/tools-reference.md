# Google Sheets MCP — Full Tool Reference
All tools use the prefix mcp__googlesheets__. Use ToolSearch to load a tool before calling it.
## Creating Spreadsheets
### create_google_sheet1
Creates an empty spreadsheet. Param: title (string, required).
### sheet_from_json
Creates spreadsheet from JSON. Params: title (string), sheet_json (array of objects), sheet_name (string).
## Reading Data
### batch_get
Retrieves cell values. Params: spreadsheet_id (string), ranges (array of strings).
### get_spreadsheet_info
Returns metadata without cell data. Param: spreadsheet_id (string).
### get_sheet_names
Lists all tab names. Param: spreadsheet_id (string).
### lookup_spreadsheet_row
Find a row by value. Params: spreadsheet_id, column, value.
## Writing Data
### spreadsheets_values_append
Append rows. Params: spreadsheet_id, range, values (2D array).
### batch_update
Update specific range. Params: spreadsheet_id, range, values.
## Structure Management
### add_sheet
Add new tab. Params: spreadsheet_id, title.
### delete_sheet
Delete tab. Params: spreadsheet_id, sheet_id.
### insert_dimension
Insert rows/columns. Params: spreadsheet_id, sheet_id, dimension, start_index, end_index.
## Formatting
### format_cell
Format cells. Params: spreadsheet_id, range, bold, fontSize, backgroundColor, foregroundColor.
### set_basic_filter
Set filter. Params: spreadsheet_id, sheet_id, range.
## Charts
### create_chart
Create chart. Params: spreadsheet_id, chart_type (BAR/LINE/AREA/COLUMN/SCATTER/COMBO), data_range, title.
## SQL Queries
### execute_sql
Run SQL (SELECT/INSERT/UPDATE/DELETE). Params: spreadsheet_id, query.
### query_table
SELECT with table discovery. Params: spreadsheet_id, sql.
## Key Concepts
- spreadsheet_id: from URL docs.google.com/spreadsheets/d/{THIS_PART}/edit
- A1 notation: Sheet1!A1:C10
- valueInputOption: USER_ENTERED or RAW
