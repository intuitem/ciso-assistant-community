[Version = "1.1.0"]
section CisoAssistant;

//
// Configuration
//
PageSize = 5000;

//
// Data source kind definition
//
CisoAssistant = [
    TestConnection = (dataSourcePath) => { "CisoAssistant.Contents", dataSourcePath },
    Authentication = [
        Key = [
            KeyLabel = Extension.LoadString("KeyLabel"),
            Label = Extension.LoadString("KeyAuthLabel")
        ]
    ],
    Label = Extension.LoadString("DataSourceLabel")
];

//
// UI publishing definition
//
CisoAssistant.Publish = [
    Beta = true,
    Category = "Online Services",
    ButtonText = { Extension.LoadString("ButtonTitle"), Extension.LoadString("ButtonHelp") },
    LearnMoreUrl = "https://intuitem.com",
    SourceImage = CisoAssistant.Icons,
    SourceTypeImage = CisoAssistant.Icons
];

CisoAssistant.Icons = [
    Icon16 = { Extension.Contents("CisoAssistant16.png"), Extension.Contents("CisoAssistant20.png"), Extension.Contents("CisoAssistant24.png"), Extension.Contents("CisoAssistant32.png") },
    Icon32 = { Extension.Contents("CisoAssistant32.png"), Extension.Contents("CisoAssistant40.png"), Extension.Contents("CisoAssistant48.png"), Extension.Contents("CisoAssistant64.png") }
];

//
// Entry point
//
[DataSource.Kind = "CisoAssistant", Publish = "CisoAssistant.Publish"]
shared CisoAssistant.Contents = Value.ReplaceType(ContentsImpl, ContentsType);

ContentsType = type function (
    BaseUrl as (Uri.Type meta [
        Documentation.FieldCaption = Extension.LoadString("BaseUrlCaption"),
        Documentation.FieldDescription = Extension.LoadString("BaseUrlDescription"),
        Documentation.SampleValues = { "https://ciso-assistant.example.com" }
    ])
) as table meta [
    Documentation.Name = "CISO Assistant",
    Documentation.LongDescription = Extension.LoadString("ContentsLongDescription")
];

ContentsImpl = (BaseUrl as text) as table =>
    let
        base = NormalizeBaseUrl(BaseUrl),
        // Forces an authenticated round-trip so bad credentials fail fast
        // (also what makes TestConnection meaningful for gateway refresh).
        check = GetJson(base, "api/build/", []),
        nav = Navigator(base)
    in
        if check <> null then nav else nav;

// The PAT travels in a request header, so cleartext HTTP is only allowed
// toward loopback/private/dev hosts; public instances must use HTTPS.
NormalizeBaseUrl = (url as text) as text =>
    let
        trimmed = Text.TrimEnd(url, "/"),
        parts = Uri.Parts(trimmed),
        host = Text.Lower(parts[Host]),
        octets = Text.Split(host, "."),
        secondOctet = if List.Count(octets) = 4 then (try Number.FromText(octets{1}) otherwise null) else null,
        isPrivateHost =
            host = "localhost"
            or Text.StartsWith(host, "127.")
            or Text.StartsWith(host, "10.")
            or Text.StartsWith(host, "192.168.")
            or (Text.StartsWith(host, "172.") and secondOctet <> null and secondOctet >= 16 and secondOctet <= 31)
            or Text.EndsWith(host, ".local"),
        allowed = parts[Scheme] = "https" or isPrivateHost
    in
        if allowed then
            trimmed
        else
            error Error.Record("DataSource.Error", Extension.LoadString("ErrorInsecureUrl"), [Host = host]);

//
// HTTP + pagination
//
AuthHeaders = () => [
    #"Authorization" = "Token " & Extension.CurrentCredential()[Key],
    #"Accept" = "application/json"
];

GetJson = (BaseUrl as text, relativePath as text, query as record) as any =>
    let
        response = Web.Contents(
            BaseUrl,
            [
                RelativePath = relativePath,
                Query = query,
                Headers = AuthHeaders(),
                ManualCredentials = true,
                ExcludedFromCacheKey = { "Authorization" },
                ManualStatusHandling = { 400, 401, 403, 404, 429, 500, 502, 503, 504 }
            ]
        ),
        status = Record.FieldOrDefault(Value.Metadata(response), "Response.Status", 200),
        result =
            if status = 401 or status = 403 then
                error Error.Record("DataSource.Error", Extension.LoadString("ErrorAuth"), [Status = status])
            else if status = 404 then
                error Error.Record("DataSource.Error", Extension.LoadString("ErrorNotFound"), [Status = status, Path = relativePath])
            else if status = 429 then
                error Error.Record("DataSource.Error", Extension.LoadString("ErrorRateLimit"), [Status = status])
            else if status >= 500 then
                error Error.Record("DataSource.Error", Text.Format(Extension.LoadString("ErrorServer"), { Number.ToText(status) }), [Status = status])
            else if status >= 400 then
                error Error.Record("DataSource.Error", Text.Format(Extension.LoadString("ErrorGeneric"), { Number.ToText(status) }), [Status = status])
            else
                Json.Document(response)
    in
        result;

// Walks DRF's {count, next, previous, results} envelope with limit/offset
// paging until every row is retrieved. Users never see any of this.
//
// The stride is the number of rows the first page actually SERVED, never the
// PageSize requested: the server caps `limit` at its own PAGINATE_MAX, and
// deriving the page count from the requested size truncates every table on an
// instance whose ceiling is lower — silently, with no error and no warning.
// Reading it back from the response keeps this correct against any ceiling,
// so the connector and the backend can be upgraded independently.
GetAllRows = (BaseUrl as text, endpoint as text, extraQuery as record) as list =>
    let
        path = "api/" & endpoint & "/",
        firstPage = GetJson(BaseUrl, path, extraQuery & [ limit = Number.ToText(PageSize), offset = "0" ]),
        firstRows = firstPage[results],
        totalCount = firstPage[count],
        served = List.Count(firstRows),
        pageCount = if served = 0 then 0 else Number.RoundUp(totalCount / served),
        remaining =
            if pageCount <= 1 then
                {}
            else
                List.Transform(
                    { 1 .. pageCount - 1 },
                    (i) => GetJson(BaseUrl, path, extraQuery & [ limit = Number.ToText(served), offset = Number.ToText(i * served) ])[results]
                )
    in
        List.Combine({ firstRows } & remaining);

// Bounded fetch for OnTake: pages up to `count` rows so previews stay
// cheap while Table.FirstN with count > PageSize remains correct.
// Same rule as GetAllRows — the first page teaches us the effective page
// size, and every subsequent offset steps by that, not by what we asked for.
GetTopRows = (BaseUrl as text, endpoint as text, extraQuery as record, count as number) as list =>
    let
        path = "api/" & endpoint & "/",
        firstLimit = List.Min({ PageSize, count }),
        firstRows = GetJson(BaseUrl, path, extraQuery & [ limit = Number.ToText(firstLimit), offset = "0" ])[results],
        served = List.Count(firstRows),
        pageCount = if served = 0 or served >= count then 0 else Number.RoundUp((count - served) / served),
        remaining = List.Transform(
            { 1 .. pageCount },
            (i) =>
                let
                    pageLimit = List.Min({ served, count - (i * served) })
                in
                    GetJson(BaseUrl, path, extraQuery & [ limit = Number.ToText(pageLimit), offset = Number.ToText(i * served) ])[results]
        )
    in
        List.FirstN(List.Combine({ firstRows } & remaining), count);

//
// Schema machinery
//
// A column spec is { name, json path, type } with an optional 4th
// element naming a value transform.
//
GetPath = (value as any, path as list) as any =>
    List.Accumulate(
        path,
        value,
        (current, fieldName) =>
            if current = null then null
            else if current is record then Record.FieldOrDefault(current, fieldName, null)
            else null
    );

ApplyTransform = (value as any, transform as nullable text) as any =>
    if value = null then null
    else if transform = null then value
    else if transform = "utcdatetime" then DateTimeZone.RemoveZone(DateTimeZone.ToUtc(DateTimeZone.FromText(value)))
    else if transform = "breadcrumb" then Text.Combine(List.Transform(value, each Record.FieldOrDefault(_, "str", "")), " / ")
    else if transform = "textlist" then Text.Combine(List.Transform(value, each Text.From(_)), ", ")
    else value;

BuildTable = (rows as list, spec as list) as table =>
    let
        columnNames = List.Transform(spec, each _{0}),
        projected = List.Transform(
            rows,
            (row) =>
                Record.FromList(
                    List.Transform(spec, (col) => ApplyTransform(GetPath(row, col{1}), if List.Count(col) > 3 then col{3} else null)),
                    columnNames
                )
        ),
        base = if List.IsEmpty(projected) then #table(columnNames, {}) else Table.FromRecords(projected, columnNames, MissingField.UseNull),
        typed = Table.TransformColumnTypes(base, List.Transform(spec, (col) => { col{0}, col{2} }))
    in
        typed;

//
// Table.View wrapper.
//
// When foldDates is true, Table.SelectRows filters of the shape
//   each [updated_at] >= RangeStart and [updated_at] < RangeEnd
// are folded into ?updated_at__gte=...&updated_at__lt=... query
// parameters, so Power BI incremental refresh only pulls the window
// instead of the full table. Unfoldable filters raise, letting the
// engine fall back to local evaluation over GetRows.
//
GetEntityTable = (BaseUrl as text, endpoint as text, spec as list, foldDates as logical, optional baseQuery as nullable record) as table =>
    let
        initialQuery = if baseQuery = null then [] else baseQuery,
        View = (extraQuery as record) =>
            Table.View(
                null,
                [
                    GetType = () => Value.Type(BuildTable({}, spec)),
                    GetRows = () => BuildTable(GetAllRows(BaseUrl, endpoint, extraQuery), spec),
                    OnTake = (count as number) =>
                        if count = 0 then
                            #table(List.Transform(spec, each _{0}), {})
                        else
                            Table.FirstN(BuildTable(GetTopRows(BaseUrl, endpoint, extraQuery, count), spec), count),
                    OnSelectRows = (selector as function) =>
                        let
                            folded = if foldDates then FoldDateFilter(RowExpression.From(selector)) else null
                        in
                            if folded = null then
                                error Error.Record("Expression.Error", "Filter cannot be folded to the CISO Assistant API")
                            else
                                @View(extraQuery & folded)
                ]
            )
    in
        View(initialQuery);

//
// Filter-folding helpers (incremental refresh)
//
FoldableFields = { "updated_at", "created_at" };

FoldDateFilter = (ast as record) as nullable record =>
    let
        kind = Record.FieldOrDefault(ast, "Kind", null),
        op = Record.FieldOrDefault(ast, "Operator", null),
        result =
            if kind = "Binary" and op = "And" then
                let
                    left = FoldDateFilter(ast[Left]),
                    right = FoldDateFilter(ast[Right])
                in
                    if left = null or right = null then null else left & right
            else if kind = "Binary" then
                FoldComparison(ast)
            else
                null
    in
        result;

FoldComparison = (node as record) as nullable record =>
    let
        left = node[Left],
        right = node[Right],
        leftKind = Record.FieldOrDefault(left, "Kind", null),
        rightKind = Record.FieldOrDefault(right, "Kind", null),
        fieldOnLeft = leftKind = "FieldAccess" and rightKind = "Constant",
        fieldOnRight = rightKind = "FieldAccess" and leftKind = "Constant",
        fieldName = if fieldOnLeft then left[MemberName] else if fieldOnRight then right[MemberName] else null,
        constValue = if fieldOnLeft then right[Value] else if fieldOnRight then left[Value] else null,
        rawOp = node[Operator],
        // Canonical operator spellings per RowExpression.From ("Equals" style,
        // with trailing s on the OrEquals forms); alternates kept defensively.
        isGte = List.Contains({ "GreaterThanOrEquals", "GreaterThanOrEqual", "GreaterOrEqual" }, rawOp),
        isLt = rawOp = "LessThan" or rawOp = "Less",
        isLte = List.Contains({ "LessThanOrEquals", "LessThanOrEqual", "LessOrEqual" }, rawOp),
        isGt = rawOp = "GreaterThan" or rawOp = "Greater",
        // Normalized to "field <op> constant" orientation:
        //   field >= C  /  C <= field  → __gte
        //   field <  C  /  C >  field  → __lt
        suffix =
            if fieldOnLeft then (if isGte then "__gte" else if isLt then "__lt" else null)
            else (if isLte then "__gte" else if isGt then "__lt" else null),
        foldable =
            fieldName <> null
            and List.Contains(FoldableFields, fieldName)
            and suffix <> null
            and (constValue is datetime or constValue is datetimezone or constValue is date)
    in
        if foldable then
            Record.FromList({ FormatDateParam(constValue) }, { fieldName & suffix })
        else
            null;

// Fact datetime columns are exposed as UTC (zone stripped), so plain
// datetime constants coming from RangeStart/RangeEnd are UTC too.
FormatDateParam = (value as any) as text =>
    let
        asDateTime =
            if value is datetimezone then DateTimeZone.RemoveZone(DateTimeZone.ToUtc(value))
            else if value is datetime then value
            else DateTime.From(value)
    in
        DateTime.ToText(asDateTime, [ Format = "yyyy-MM-dd'T'HH:mm:ss.fff" ]) & "Z";

//
// Bridge tables: derived from the M2M arrays already present in the
// (IAM-scoped) fact payloads, so they can never expose rows the user
// cannot read.
//
// A bridge re-reads its parent endpoint, and several bridges share one
// parent, so a refresh scans some endpoints half a dozen times. `?fields=`
// narrows each of those scans to the identifier and the one M2M column the
// bridge needs. The parameter is a recent addition on the API side: older
// instances ignore unknown query parameters and return the full row, which
// still works, and anything else falls back to the unnarrowed request rather
// than failing a refresh over an optimisation.
//
GetBridgeRows = (BaseUrl as text, endpoint as text, listField as text) as list =>
    let
        narrowed = try GetAllRows(BaseUrl, endpoint, [ fields = "id," & listField ])
    in
        if narrowed[HasError] then GetAllRows(BaseUrl, endpoint, []) else narrowed[Value];

GetBridgeTable = (BaseUrl as text, endpoint as text, parentColumn as text, listField as text, childColumn as text) as table =>
    let
        rows = GetBridgeRows(BaseUrl, endpoint, listField),
        pairs = List.Combine(
            List.Transform(
                rows,
                (row) =>
                    let
                        children = Record.FieldOrDefault(row, listField, {})
                    in
                        List.Transform(
                            if children = null then {} else children,
                            // M2M arrays are either {id, str} records or plain id strings
                            (child) => Record.FromList(
                                { row[id], if child is record then Record.FieldOrDefault(child, "id", null) else Text.From(child) },
                                { parentColumn, childColumn }
                            )
                        )
            )
        ),
        base = if List.IsEmpty(pairs) then #table({ parentColumn, childColumn }, {}) else Table.FromRecords(pairs, { parentColumn, childColumn }, MissingField.UseNull),
        typed = Table.TransformColumnTypes(base, { { parentColumn, type text }, { childColumn, type text } })
    in
        typed;

//
// Column specs — hard-coded v1 contract, mirrored by
// automation/powerbi/contract.json and enforced by
// backend/app_tests/api/test_api_powerbi_contract.py.
//
RequirementAssessmentSpec = {
    { "id", { "id" }, type text },
    { "name", { "name" }, type text },
    { "description", { "description" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "compliance_assessment_id", { "compliance_assessment", "id" }, type text },
    { "compliance_assessment_name", { "compliance_assessment", "name" }, type text },
    { "perimeter_id", { "perimeter", "id" }, type text },
    { "perimeter_name", { "perimeter", "str" }, type text },
    { "requirement_id", { "requirement", "id" }, type text },
    { "requirement_ref_id", { "requirement", "ref_id" }, type text },
    { "requirement_name", { "requirement", "name" }, type text },
    { "requirement_urn", { "requirement", "urn" }, type text },
    { "assessable", { "assessable" }, type logical },
    { "status", { "status" }, type text },
    { "result", { "result" }, type text },
    { "extended_result", { "extended_result" }, type text },
    { "is_scored", { "is_scored" }, type logical },
    { "score", { "score" }, Int64.Type },
    { "documentation_score", { "documentation_score" }, Int64.Type },
    { "target_score", { "target_score" }, type number },
    { "observation", { "observation" }, type text },
    { "eta", { "eta" }, type date },
    { "due_date", { "due_date" }, type date },
    { "selected", { "selected" }, type logical },
    { "is_locked", { "is_locked" }, type logical },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

AppliedControlSpec = {
    { "id", { "id" }, type text },
    { "name", { "name" }, type text },
    { "description", { "description" }, type text },
    { "ref_id", { "ref_id" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "reference_control_id", { "reference_control", "id" }, type text },
    { "reference_control_name", { "reference_control", "str" }, type text },
    { "status", { "status" }, type text },
    { "category", { "category" }, type text },
    { "csf_function", { "csf_function" }, type text },
    { "priority", { "priority" }, type text },
    { "effort", { "effort" }, type text },
    { "control_impact", { "control_impact" }, type text },
    { "start_date", { "start_date" }, type date },
    { "eta", { "eta" }, type date },
    { "expiry_date", { "expiry_date" }, type date },
    { "progress", { "progress_field" }, Int64.Type },
    { "is_assigned", { "is_assigned" }, type logical },
    { "link", { "link" }, type text },
    { "observation", { "observation" }, type text },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

FindingSpec = {
    { "id", { "id" }, type text },
    { "name", { "name" }, type text },
    { "description", { "description" }, type text },
    { "ref_id", { "ref_id" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "folder_path", { "path" }, type text, "breadcrumb" },
    { "findings_assessment_id", { "findings_assessment", "id" }, type text },
    { "findings_assessment_name", { "findings_assessment", "name" }, type text },
    { "requirement_node_id", { "requirement_node", "id" }, type text },
    { "requirement_node_name", { "requirement_node", "name" }, type text },
    { "asset_id", { "asset", "id" }, type text },
    { "asset_name", { "asset", "str" }, type text },
    { "perimeter_id", { "perimeter", "id" }, type text },
    { "perimeter_name", { "perimeter", "name" }, type text },
    { "severity", { "severity" }, type text },
    { "priority", { "priority" }, type text },
    { "status", { "status" }, type text },
    { "eta", { "eta" }, type date },
    { "due_date", { "due_date" }, type date },
    { "observation", { "observation" }, type text },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

EvidenceSpec = {
    { "id", { "id" }, type text },
    { "name", { "name" }, type text },
    { "description", { "description" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "folder_path", { "path" }, type text, "breadcrumb" },
    { "status", { "status" }, type text },
    { "expiry_date", { "expiry_date" }, type date },
    { "link", { "link" }, type text },
    { "attachment", { "attachment" }, type text },
    { "size", { "size" }, type text },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

IncidentSpec = {
    { "id", { "id" }, type text },
    { "name", { "name" }, type text },
    { "description", { "description" }, type text },
    { "ref_id", { "ref_id" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "folder_path", { "path" }, type text, "breadcrumb" },
    { "severity", { "severity" }, type text },
    { "status", { "status" }, type text },
    { "detection", { "detection" }, type text },
    { "reported_at", { "reported_at" }, type datetime, "utcdatetime" },
    { "occurred_at", { "occurred_at" }, type datetime, "utcdatetime" },
    { "resolved_at", { "resolved_at" }, type datetime, "utcdatetime" },
    { "resolution", { "resolution" }, type text },
    { "is_bcp_activated", { "is_bcp_activated" }, type logical },
    { "link", { "link" }, type text },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

ComplianceAssessmentSpec = {
    { "id", { "id" }, type text },
    { "name", { "name" }, type text },
    { "description", { "description" }, type text },
    { "ref_id", { "ref_id" }, type text },
    { "version", { "version" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "folder_path", { "path" }, type text, "breadcrumb" },
    { "perimeter_id", { "perimeter", "id" }, type text },
    { "perimeter_name", { "perimeter", "str" }, type text },
    { "framework_id", { "framework", "id" }, type text },
    { "framework_name", { "framework", "str" }, type text },
    { "status", { "status" }, type text },
    { "eta", { "eta" }, type date },
    { "due_date", { "due_date" }, type date },
    { "progress", { "progress" }, Int64.Type },
    { "is_locked", { "is_locked" }, type logical },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

FrameworkSpec = {
    { "id", { "id" }, type text },
    { "urn", { "urn" }, type text },
    { "ref_id", { "ref_id" }, type text },
    { "name", { "name" }, type text },
    { "description", { "description" }, type text },
    { "provider", { "provider" }, type text },
    { "locale", { "locale" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "library_id", { "library", "id" }, type text },
    { "library_name", { "library", "str" }, type text },
    { "min_score", { "min_score" }, Int64.Type },
    { "max_score", { "max_score" }, Int64.Type },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

RequirementNodeSpec = {
    { "id", { "id" }, type text },
    { "urn", { "urn" }, type text },
    { "ref_id", { "ref_id" }, type text },
    { "name", { "name" }, type text },
    { "description", { "description" }, type text },
    { "parent_urn", { "parent_urn" }, type text },
    { "framework_id", { "framework" }, type text },
    { "order_id", { "order_id" }, Int64.Type },
    { "assessable", { "assessable" }, type logical },
    { "weight", { "weight" }, Int64.Type },
    { "implementation_groups", { "implementation_groups" }, type text, "textlist" },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

RiskScenarioSpec = {
    { "id", { "id" }, type text },
    { "ref_id", { "ref_id" }, type text },
    { "name", { "name" }, type text },
    { "description", { "description" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "risk_assessment_id", { "risk_assessment", "id" }, type text },
    { "risk_assessment_name", { "risk_assessment", "str" }, type text },
    { "treatment", { "treatment" }, type text },
    { "current_level_name", { "current_level", "name" }, type text },
    { "current_level_value", { "current_level", "value" }, Int64.Type },
    { "current_level_color", { "current_level", "hexcolor" }, type text },
    { "residual_level_name", { "residual_level", "name" }, type text },
    { "residual_level_value", { "residual_level", "value" }, Int64.Type },
    { "residual_level_color", { "residual_level", "hexcolor" }, type text },
    { "within_tolerance", { "within_tolerance" }, type text },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

VulnerabilitySpec = {
    { "id", { "id" }, type text },
    { "ref_id", { "ref_id" }, type text },
    { "name", { "name" }, type text },
    { "description", { "description" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "folder_path", { "path" }, type text, "breadcrumb" },
    { "severity", { "severity" }, type text },
    { "status", { "status" }, type text },
    { "sla_state", { "state", "name" }, type text },
    { "sla_state_color", { "state", "hexcolor" }, type text },
    { "detected_at", { "detected_at" }, type date },
    { "published_date", { "published_date" }, type date },
    { "eta", { "eta" }, type date },
    { "due_date", { "due_date" }, type date },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

SecurityExceptionSpec = {
    { "id", { "id" }, type text },
    { "ref_id", { "ref_id" }, type text },
    { "name", { "name" }, type text },
    { "description", { "description" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "folder_path", { "path" }, type text, "breadcrumb" },
    { "severity", { "severity" }, type text },
    { "status", { "status" }, type text },
    { "expiration_date", { "expiration_date" }, type date },
    { "associated_objects_count", { "associated_objects_count" }, Int64.Type },
    { "link", { "link" }, type text },
    { "observation", { "observation" }, type text },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

AssetSpec = {
    { "id", { "id" }, type text },
    { "ref_id", { "ref_id" }, type text },
    { "name", { "name" }, type text },
    { "description", { "description" }, type text },
    { "type", { "type" }, type text },
    { "is_primary", { "is_primary" }, type logical },
    { "is_business_function", { "is_business_function" }, type logical },
    { "asset_class_id", { "asset_class", "id" }, type text },
    { "asset_class_name", { "asset_class", "str" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

RiskAssessmentSpec = {
    { "id", { "id" }, type text },
    { "ref_id", { "ref_id" }, type text },
    { "name", { "name" }, type text },
    { "description", { "description" }, type text },
    { "version", { "version" }, type text },
    { "status", { "status" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "folder_path", { "path" }, type text, "breadcrumb" },
    { "perimeter_id", { "perimeter", "id" }, type text },
    { "perimeter_name", { "perimeter", "str" }, type text },
    { "risk_matrix_id", { "risk_matrix", "id" }, type text },
    { "risk_matrix_name", { "risk_matrix", "str" }, type text },
    { "risk_scenarios_count", { "risk_scenarios_count" }, Int64.Type },
    { "eta", { "eta" }, type date },
    { "due_date", { "due_date" }, type date },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

PerimeterSpec = {
    { "id", { "id" }, type text },
    { "ref_id", { "ref_id" }, type text },
    { "name", { "name" }, type text },
    { "description", { "description" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "lc_status", { "lc_status" }, type text },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

ThreatSpec = {
    { "id", { "id" }, type text },
    { "urn", { "urn" }, type text },
    { "ref_id", { "ref_id" }, type text },
    { "name", { "name" }, type text },
    { "description", { "description" }, type text },
    { "provider", { "provider" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "library_id", { "library", "id" }, type text },
    { "library_name", { "library", "str" }, type text },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

ReferenceControlSpec = {
    { "id", { "id" }, type text },
    { "urn", { "urn" }, type text },
    { "ref_id", { "ref_id" }, type text },
    { "name", { "name" }, type text },
    { "description", { "description" }, type text },
    { "provider", { "provider" }, type text },
    { "category", { "category" }, type text },
    { "csf_function", { "csf_function" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "library_id", { "library", "id" }, type text },
    { "library_name", { "library", "str" }, type text },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

FindingsAssessmentSpec = {
    { "id", { "id" }, type text },
    { "ref_id", { "ref_id" }, type text },
    { "name", { "name" }, type text },
    { "description", { "description" }, type text },
    { "category", { "category" }, type text },
    { "status", { "status" }, type text },
    { "version", { "version" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "folder_path", { "path" }, type text, "breadcrumb" },
    { "perimeter_id", { "perimeter", "id" }, type text },
    { "perimeter_name", { "perimeter", "str" }, type text },
    { "findings_count", { "findings_count" }, Int64.Type },
    { "treatment_progress", { "treatment_progress" }, Int64.Type },
    { "eta", { "eta" }, type date },
    { "due_date", { "due_date" }, type date },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

FilteringLabelSpec = {
    { "id", { "id" }, type text },
    { "label", { "label" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

FolderSpec = {
    { "id", { "id" }, type text },
    { "name", { "name" }, type text },
    { "description", { "description" }, type text },
    { "full_path", { "path" }, type text, "breadcrumb" },
    { "parent_folder_id", { "parent_folder", "id" }, type text },
    { "parent_folder_name", { "parent_folder", "str" }, type text },
    { "content_type", { "content_type" }, type text },
    { "builtin", { "builtin" }, type logical },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

TaskNodeSpec = {
    { "id", { "id" }, type text },
    { "name", { "name" }, type text },
    { "task_template_id", { "task_template", "id" }, type text },
    { "task_template_name", { "task_template", "str" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "status", { "status" }, type text },
    { "due_date", { "due_date" }, type date },
    { "scheduled_date", { "scheduled_date" }, type date },
    { "is_recurrent", { "is_recurrent" }, type logical },
    { "observation", { "observation" }, type text },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

EntityAssessmentSpec = {
    { "id", { "id" }, type text },
    { "name", { "name" }, type text },
    { "description", { "description" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "entity_id", { "entity", "id" }, type text },
    { "entity_name", { "entity", "str" }, type text },
    { "perimeter_id", { "perimeter", "id" }, type text },
    { "perimeter_name", { "perimeter", "str" }, type text },
    { "compliance_assessment_id", { "compliance_assessment", "id" }, type text },
    { "compliance_assessment_name", { "compliance_assessment", "str" }, type text },
    { "status", { "status" }, type text },
    { "conclusion", { "conclusion" }, type text },
    { "criticality", { "criticality" }, Int64.Type },
    // Respondent-side progress; review_progress is the auditor's.
    { "completion", { "completion" }, Int64.Type },
    { "review_progress", { "review_progress" }, Int64.Type },
    { "version", { "version" }, type text },
    { "eta", { "eta" }, type date },
    { "due_date", { "due_date" }, type date },
    { "expiry_date", { "expiry_date" }, type date },
    { "is_locked", { "is_locked" }, type logical },
    { "observation", { "observation" }, type text },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

ContractSpec = {
    { "id", { "id" }, type text },
    { "name", { "name" }, type text },
    { "ref_id", { "ref_id" }, type text },
    { "description", { "description" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "provider_entity_id", { "provider_entity", "id" }, type text },
    { "provider_entity_name", { "provider_entity", "str" }, type text },
    { "beneficiary_entity_id", { "beneficiary_entity", "id" }, type text },
    { "beneficiary_entity_name", { "beneficiary_entity", "str" }, type text },
    { "overarching_contract_id", { "overarching_contract", "id" }, type text },
    { "status", { "status" }, type text },
    { "start_date", { "start_date" }, type date },
    { "end_date", { "end_date" }, type date },
    { "annual_expense", { "annual_expense" }, type number },
    { "currency", { "currency" }, type text },
    { "is_intragroup", { "is_intragroup" }, type logical },
    { "notice_period_entity", { "notice_period_entity" }, Int64.Type },
    { "notice_period_provider", { "notice_period_provider" }, Int64.Type },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

RiskAcceptanceSpec = {
    { "id", { "id" }, type text },
    { "name", { "name" }, type text },
    { "description", { "description" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "approver_id", { "approver", "id" }, type text },
    { "approver_name", { "approver", "str" }, type text },
    { "state", { "state" }, type text },
    { "expiry_date", { "expiry_date" }, type date },
    { "accepted_at", { "accepted_at" }, type datetime, "utcdatetime" },
    { "rejected_at", { "rejected_at" }, type datetime, "utcdatetime" },
    { "revoked_at", { "revoked_at" }, type datetime, "utcdatetime" },
    { "justification", { "justification" }, type text },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

// The dimension that makes owner/assignee columns reportable: every
// owner-style M2M in the API points here, whether it wraps a user, a team
// or an entity.
ActorSpec = {
    { "id", { "id" }, type text },
    { "name", { "str" }, type text },
    { "type", { "type" }, type text },
    { "specific_id", { "specific", "id" }, type text },
    { "specific_name", { "specific", "str" }, type text }
};

EntitySpec = {
    { "id", { "id" }, type text },
    { "name", { "name" }, type text },
    { "ref_id", { "ref_id" }, type text },
    { "description", { "description" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "parent_entity_id", { "parent_entity", "id" }, type text },
    { "parent_entity_name", { "parent_entity", "str" }, type text },
    { "is_active", { "is_active" }, type logical },
    { "builtin", { "builtin" }, type logical },
    { "mission", { "mission" }, type text },
    { "country", { "country" }, type text },
    { "currency", { "currency" }, type text },
    { "default_criticality", { "default_criticality" }, type number },
    { "last_assessment_status", { "last_assessment_status" }, type text },
    { "last_assessment_date", { "last_assessment_date" }, type datetime, "utcdatetime" },
    { "subcontracts_count", { "subcontracts_count" }, Int64.Type },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

SolutionSpec = {
    { "id", { "id" }, type text },
    { "name", { "name" }, type text },
    { "ref_id", { "ref_id" }, type text },
    { "description", { "description" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "provider_entity_id", { "provider_entity", "id" }, type text },
    { "provider_entity_name", { "provider_entity", "str" }, type text },
    { "recipient_entity_id", { "recipient_entity", "id" }, type text },
    { "recipient_entity_name", { "recipient_entity", "str" }, type text },
    { "criticality", { "criticality" }, Int64.Type },
    { "is_active", { "is_active" }, type logical },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

TaskTemplateSpec = {
    { "id", { "id" }, type text },
    { "name", { "name" }, type text },
    { "ref_id", { "ref_id" }, type text },
    { "description", { "description" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "task_date", { "task_date" }, type date },
    { "is_recurrent", { "is_recurrent" }, type logical },
    { "enabled", { "enabled" }, type logical },
    // Null on a recurrent definition: there the state lives on the occurrences.
    { "status", { "status" }, type text },
    { "last_occurrence_status", { "last_occurrence_status" }, type text },
    { "next_occurrence_status", { "next_occurrence_status" }, type text },
    { "next_occurrence", { "next_occurrence" }, type date },
    { "link", { "link" }, type text },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

CampaignSpec = {
    { "id", { "id" }, type text },
    { "name", { "name" }, type text },
    { "description", { "description" }, type text },
    { "folder_id", { "folder", "id" }, type text },
    { "folder_name", { "folder", "str" }, type text },
    { "status", { "status" }, type text },
    { "kind", { "kind" }, type text },
    { "start_date", { "start_date" }, type date },
    { "eta", { "eta" }, type date },
    { "due_date", { "due_date" }, type date },
    { "created_at", { "created_at" }, type datetime, "utcdatetime" },
    { "updated_at", { "updated_at" }, type datetime, "utcdatetime" }
};

//
// Navigator
//
Navigator = (base as text) as table =>
    let
        facts = #table(
            { "Name", "Data", "ItemKind", "ItemName", "IsLeaf" },
            {
                { "Requirement Assessments", GetEntityTable(base, "requirement-assessments", RequirementAssessmentSpec, true), "Table", "Table", true },
                { "Applied Controls", GetEntityTable(base, "applied-controls", AppliedControlSpec, true), "Table", "Table", true },
                { "Findings", GetEntityTable(base, "findings", FindingSpec, true), "Table", "Table", true },
                { "Evidences", GetEntityTable(base, "evidences", EvidenceSpec, true), "Table", "Table", true },
                { "Incidents", GetEntityTable(base, "incidents", IncidentSpec, true), "Table", "Table", true },
                { "Risk Scenarios", GetEntityTable(base, "risk-scenarios", RiskScenarioSpec, true), "Table", "Table", true },
                { "Vulnerabilities", GetEntityTable(base, "vulnerabilities", VulnerabilitySpec, true), "Table", "Table", true },
                { "Security Exceptions", GetEntityTable(base, "security-exceptions", SecurityExceptionSpec, true), "Table", "Table", true },
                { "Assets", GetEntityTable(base, "assets", AssetSpec, true), "Table", "Table", true },
                // Appended, never inserted: reports built on connector <= 1.0.1
                // navigate by position (see ToNavigationTable).
                { "Task Nodes", GetEntityTable(base, "task-nodes", TaskNodeSpec, true), "Table", "Table", true },
                { "Entity Assessments", GetEntityTable(base, "entity-assessments", EntityAssessmentSpec, true), "Table", "Table", true },
                { "Contracts", GetEntityTable(base, "contracts", ContractSpec, true), "Table", "Table", true },
                { "Risk Acceptances", GetEntityTable(base, "risk-acceptances", RiskAcceptanceSpec, true), "Table", "Table", true }
            }
        ),
        dimensions = #table(
            { "Name", "Data", "ItemKind", "ItemName", "IsLeaf" },
            {
                { "Compliance Assessments", GetEntityTable(base, "compliance-assessments", ComplianceAssessmentSpec, false), "Table", "Table", true },
                { "Frameworks", GetEntityTable(base, "frameworks", FrameworkSpec, false), "Table", "Table", true },
                { "Requirement Nodes", GetEntityTable(base, "requirement-nodes", RequirementNodeSpec, false), "Table", "Table", true },
                { "Folders", GetEntityTable(base, "folders", FolderSpec, false), "Table", "Table", true },
                { "Risk Assessments", GetEntityTable(base, "risk-assessments", RiskAssessmentSpec, false), "Table", "Table", true },
                { "Perimeters", GetEntityTable(base, "perimeters", PerimeterSpec, false), "Table", "Table", true },
                { "Threats", GetEntityTable(base, "threats", ThreatSpec, false), "Table", "Table", true },
                { "Reference Controls", GetEntityTable(base, "reference-controls", ReferenceControlSpec, false), "Table", "Table", true },
                { "Findings Assessments", GetEntityTable(base, "findings-assessments", FindingsAssessmentSpec, false), "Table", "Table", true },
                { "Labels", GetEntityTable(base, "filtering-labels", FilteringLabelSpec, false), "Table", "Table", true },
                // The endpoint hides third-party actors by default, since it
                // mainly serves assignee pickers. A dimension has to cover every
                // id the ownership bridges can carry, or those rows join to
                // nothing, so ask for them explicitly.
                { "Actors", GetEntityTable(base, "actors", ActorSpec, false, [ include_third_parties = "true" ]), "Table", "Table", true },
                { "Entities", GetEntityTable(base, "entities", EntitySpec, false), "Table", "Table", true },
                { "Solutions", GetEntityTable(base, "solutions", SolutionSpec, false), "Table", "Table", true },
                { "Task Templates", GetEntityTable(base, "task-templates", TaskTemplateSpec, false), "Table", "Table", true },
                { "Campaigns", GetEntityTable(base, "campaigns", CampaignSpec, false), "Table", "Table", true }
            }
        ),
        bridges = #table(
            { "Name", "Data", "ItemKind", "ItemName", "IsLeaf" },
            {
                { "Requirement Assessment - Applied Control", GetBridgeTable(base, "requirement-assessments", "requirement_assessment_id", "applied_controls", "applied_control_id"), "Table", "Table", true },
                { "Requirement Assessment - Evidence", GetBridgeTable(base, "requirement-assessments", "requirement_assessment_id", "evidences", "evidence_id"), "Table", "Table", true },
                // Derived from the evidences endpoint: the applied-controls
                // LIST serializer intentionally omits its evidences M2M.
                { "Applied Control - Evidence", GetBridgeTable(base, "evidences", "evidence_id", "applied_controls", "applied_control_id"), "Table", "Table", true },
                { "Finding - Applied Control", GetBridgeTable(base, "findings", "finding_id", "applied_controls", "applied_control_id"), "Table", "Table", true },
                { "Incident - Applied Control", GetBridgeTable(base, "incidents", "incident_id", "applied_controls", "applied_control_id"), "Table", "Table", true },
                { "Incident - Asset", GetBridgeTable(base, "incidents", "incident_id", "assets", "asset_id"), "Table", "Table", true },
                { "Incident - Threat", GetBridgeTable(base, "incidents", "incident_id", "threats", "threat_id"), "Table", "Table", true },
                { "Finding - Vulnerability", GetBridgeTable(base, "findings", "finding_id", "vulnerabilities", "vulnerability_id"), "Table", "Table", true },
                { "Risk Scenario - Asset", GetBridgeTable(base, "risk-scenarios", "risk_scenario_id", "assets", "asset_id"), "Table", "Table", true },
                { "Risk Scenario - Threat", GetBridgeTable(base, "risk-scenarios", "risk_scenario_id", "threats", "threat_id"), "Table", "Table", true },
                { "Risk Scenario - Applied Control", GetBridgeTable(base, "risk-scenarios", "risk_scenario_id", "applied_controls", "applied_control_id"), "Table", "Table", true },
                { "Risk Scenario - Vulnerability", GetBridgeTable(base, "risk-scenarios", "risk_scenario_id", "vulnerabilities", "vulnerability_id"), "Table", "Table", true },
                { "Vulnerability - Asset", GetBridgeTable(base, "vulnerabilities", "vulnerability_id", "assets", "asset_id"), "Table", "Table", true },
                { "Vulnerability - Applied Control", GetBridgeTable(base, "vulnerabilities", "vulnerability_id", "applied_controls", "applied_control_id"), "Table", "Table", true },
                { "Asset - Parent Asset", GetBridgeTable(base, "assets", "asset_id", "parent_assets", "parent_asset_id"), "Table", "Table", true },
                { "Applied Control - Label", GetBridgeTable(base, "applied-controls", "applied_control_id", "filtering_labels", "label_id"), "Table", "Table", true },
                { "Finding - Label", GetBridgeTable(base, "findings", "finding_id", "filtering_labels", "label_id"), "Table", "Table", true },
                { "Incident - Label", GetBridgeTable(base, "incidents", "incident_id", "filtering_labels", "label_id"), "Table", "Table", true },
                { "Risk Scenario - Label", GetBridgeTable(base, "risk-scenarios", "risk_scenario_id", "filtering_labels", "label_id"), "Table", "Table", true },
                { "Vulnerability - Label", GetBridgeTable(base, "vulnerabilities", "vulnerability_id", "filtering_labels", "label_id"), "Table", "Table", true },
                // Ownership: every one of these M2Ms points at Actor, so they
                // all join to the Actors dimension.
                { "Applied Control - Owner", GetBridgeTable(base, "applied-controls", "applied_control_id", "owner", "actor_id"), "Table", "Table", true },
                { "Finding - Owner", GetBridgeTable(base, "findings", "finding_id", "owner", "actor_id"), "Table", "Table", true },
                { "Risk Scenario - Owner", GetBridgeTable(base, "risk-scenarios", "risk_scenario_id", "owner", "actor_id"), "Table", "Table", true },
                { "Asset - Owner", GetBridgeTable(base, "assets", "asset_id", "owner", "actor_id"), "Table", "Table", true },
                { "Incident - Owner", GetBridgeTable(base, "incidents", "incident_id", "owners", "actor_id"), "Table", "Table", true },
                { "Contract - Owner", GetBridgeTable(base, "contracts", "contract_id", "owner", "actor_id"), "Table", "Table", true },
                { "Task Node - Assignee", GetBridgeTable(base, "task-nodes", "task_node_id", "assigned_to", "actor_id"), "Table", "Table", true },
                { "Task Template - Assignee", GetBridgeTable(base, "task-templates", "task_template_id", "assigned_to", "actor_id"), "Table", "Table", true },
                { "Applied Control - Asset", GetBridgeTable(base, "applied-controls", "applied_control_id", "assets", "asset_id"), "Table", "Table", true },
                { "Task Node - Applied Control", GetBridgeTable(base, "task-nodes", "task_node_id", "applied_controls", "applied_control_id"), "Table", "Table", true },
                { "Task Template - Applied Control", GetBridgeTable(base, "task-templates", "task_template_id", "applied_controls", "applied_control_id"), "Table", "Table", true },
                { "Risk Acceptance - Risk Scenario", GetBridgeTable(base, "risk-acceptances", "risk_acceptance_id", "risk_scenarios", "risk_scenario_id"), "Table", "Table", true },
                { "Entity Assessment - Solution", GetBridgeTable(base, "entity-assessments", "entity_assessment_id", "solutions", "solution_id"), "Table", "Table", true },
                { "Contract - Solution", GetBridgeTable(base, "contracts", "contract_id", "solutions", "solution_id"), "Table", "Table", true },
                { "Solution - Asset", GetBridgeTable(base, "solutions", "solution_id", "assets", "asset_id"), "Table", "Table", true },
                { "Campaign - Compliance Assessment", GetBridgeTable(base, "campaigns", "campaign_id", "compliance_assessments", "compliance_assessment_id"), "Table", "Table", true }
            }
        ),
        root = #table(
            { "Name", "Data", "ItemKind", "ItemName", "IsLeaf" },
            {
                { "Facts", ToNavigationTable(facts), "Folder", "Folder", false },
                { "Dimensions", ToNavigationTable(dimensions), "Folder", "Folder", false },
                { "Bridges", ToNavigationTable(bridges), "Folder", "Folder", false }
            }
        )
    in
        ToNavigationTable(root);

// The "Name" key is what makes Power BI Desktop generate key-based
// navigation steps ({[Name = "Applied Controls"]}) instead of positional
// ones ({1}). Without it, inserting or reordering a navigator entry silently
// repoints every existing report's query at a different table.
ToNavigationTable = (tbl as table) as table =>
    let
        tableType = Value.Type(tbl),
        newTableType = Type.AddTableKey(tableType, { "Name" }, true) meta [
            NavigationTable.NameColumn = "Name",
            NavigationTable.DataColumn = "Data",
            NavigationTable.ItemKindColumn = "ItemKind",
            Preview.DelayColumn = "ItemName",
            NavigationTable.IsLeafColumn = "IsLeaf"
        ]
    in
        Value.ReplaceType(tbl, newTableType);
