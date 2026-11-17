// Test query for PQTest / the SDK "Evaluate current file" task.
// Set a Key credential first (your CISO Assistant Personal Access Token).
//
// Point the URL at your own instance before evaluating (plain HTTP is fine
// against a local dev server; always use HTTPS for real instances — the PAT
// travels in a request header).
//
// Keep the URL a literal inside the CisoAssistant.Contents call — the SDK
// resolves the data source (for credential binding) by static analysis and
// fails on variable indirection.
//
// Returns the top-level navigator. To drill into a table during testing:
//   CisoAssistant.Contents("...") {[Name = "Facts"]}[Data] {[Name = "Applied Controls"]}[Data]
CisoAssistant.Contents("https://localhost:8443")
