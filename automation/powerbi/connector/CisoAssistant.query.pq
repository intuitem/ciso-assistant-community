// Test query for PQTest / the SDK "Evaluate current file" task.
// Set a Key credential first (your CISO Assistant Personal Access Token).
//
// Keep the URL a literal inside the CisoAssistant.Contents call — the SDK
// resolves the data source (for credential binding) by static analysis and
// fails on variable indirection.
//
// Returns the top-level navigator. To drill into a table during testing:
//   CisoAssistant.Contents("...") {[Name = "Facts"]}[Data] {[Name = "Applied Controls"]}[Data]
// CisoAssistant.Contents("http://10.211.55.2:8000")
//CisoAssistant.Contents("http://10.211.55.2:8000"){[Name = "Facts"]}[Data]{[Name = "Applied Controls"]}[Data]
Table.SelectRows(CisoAssistant.Contents("http://10.211.55.2:8000"){[Name = "Facts"]}[Data]{[Name = "Applied Controls"]}[Data], each [updated_at] >= #datetime(2026,7,1,0,0,0) and [updated_at] < #datetime(2026,7,23,0,0,0))
