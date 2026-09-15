$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$script:Passed = 0
$SchemaNamespace = 'http://www.w3.org/2001/XMLSchema'

function Assert-Profile {
    param([bool] $Condition, [string] $Name)
    if (-not $Condition) {
        throw "Failed: $Name"
    }
    $script:Passed++
    Write-Output "PASS $Name"
}

function Read-NativeSchema {
    param([string] $Xml)
    $settings = [System.Xml.XmlReaderSettings]::new()
    $settings.DtdProcessing = [System.Xml.DtdProcessing]::Prohibit
    $settings.XmlResolver = $null
    $document = [System.Xml.XmlDocument]::new()
    $document.XmlResolver = $null
    $reader = [System.Xml.XmlReader]::Create(
        [System.IO.StringReader]::new($Xml), $settings
    )
    try {
        $document.Load($reader)
    }
    finally {
        $reader.Dispose()
    }
    $schemas = [System.Xml.Schema.XmlSchemaSet]::new()
    $schemas.XmlResolver = $null
    $schemaReader = [System.Xml.XmlNodeReader]::new($document)
    try {
        $null = $schemas.Add($document.DocumentElement.GetAttribute('targetNamespace'), $schemaReader)
        $schemas.Compile()
    }
    finally {
        $schemaReader.Dispose()
    }
    return ,$document
}

function Select-XsdDeclaration {
    param([System.Xml.XmlDocument] $Document, [string] $Expression)
    $namespaces = [System.Xml.XmlNamespaceManager]::new($Document.NameTable)
    foreach ($attribute in $Document.DocumentElement.Attributes) {
        if ($attribute.Prefix -ceq 'xmlns') {
            $namespaces.AddNamespace($attribute.LocalName, $attribute.Value)
        }
    }
    $namespaces.AddNamespace('xs', $SchemaNamespace)
    $namespaces.AddNamespace('xml', 'http://www.w3.org/XML/1998/namespace')
    if ([string]::IsNullOrEmpty($Expression)) {
        $Expression = '/xs:schema/xs:element | /xs:schema/xs:simpleType | /xs:schema/xs:complexType'
    }
    $result = $Document.CreateNavigator().Evaluate($Expression, $namespaces)
    if ($result -isnot [System.Xml.XPath.XPathNodeIterator] -or $result.Count -ne 1) {
        throw [System.InvalidOperationException]::new('Exactly one declaration is required')
    }
    $null = $result.MoveNext()
    $node = $result.Current.UnderlyingObject
    if ($node -isnot [System.Xml.XmlElement] -or
        $node.NamespaceURI -cne $SchemaNamespace -or
        $node.LocalName -cnotin @('element', 'simpleType', 'complexType') -or
        ($node.LocalName -ceq 'element' -and $node.HasAttribute('ref'))) {
        throw [System.InvalidOperationException]::new('Target is not a declaration')
    }
    return ,$node
}

function Assert-SelectionRejected {
    param([System.Xml.XmlDocument] $Document, [string] $Expression, [string] $Name)
    try {
        $null = Select-XsdDeclaration $Document $Expression
    }
    catch [System.InvalidOperationException] {
        Assert-Profile $true $Name
        return
    }
    throw "Expected a selection error: $Name"
}

$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$spec = Get-Content -LiteralPath (Join-Path $root 'schema\spec.md') -Raw
$section = ($spec -split '#### 4.3.2. XML Schema', 2)[1]
$section = ($section -split '#### 4.3.3.', 2)[0]
$xml = [regex]::Match($section, '```xml\r?\n(.*?)\r?\n```', 'Singleline').Groups[1].Value
$uri = [regex]::Match(
    $section, '`(https://example.com/schemas/orders.xsd#[^`]+)`'
).Groups[1].Value
Assert-Profile ($xml.Length -gt 0 -and $uri.Length -gt 0) 'actual_markdown_inputs'
$document = Read-NativeSchema $xml
$expression = [System.Uri]::UnescapeDataString(($uri -split '#', 2)[1])
$selected = Select-XsdDeclaration $document $expression
Assert-Profile ($selected.GetAttribute('name') -ceq 'Order') 'encoded_xpath_selects_documented_order'
$selected = Select-XsdDeclaration $document "/xs:schema/xs:element[@name='Cancel']"
Assert-Profile ($selected.GetAttribute('name') -ceq 'Cancel') 'distinct_declaration_not_first_root'
Assert-SelectionRejected $document '' 'multiple_global_roots_require_selector'
Assert-SelectionRejected $document '/xs:schema/xs:element' 'multiple_xpath_matches_rejected'
Assert-SelectionRejected $document "/xs:schema/xs:element[@name='Missing']" 'missing_xpath_target_rejected'
Assert-SelectionRejected $document 'count(/xs:schema/xs:element)' 'number_result_rejected'
Assert-SelectionRejected $document 'true()' 'boolean_result_rejected'
Assert-SelectionRejected $document "string('Order')" 'string_result_rejected'
Assert-SelectionRejected $document '/xs:schema' 'schema_container_not_declaration'

foreach ($body in @(
    '<xs:element name="Only" type="xs:string"/>',
    '<xs:simpleType name="Only"><xs:restriction base="xs:string"/></xs:simpleType>',
    '<xs:complexType name="Only"><xs:sequence/></xs:complexType>'
)) {
    $single = Read-NativeSchema "<xs:schema xmlns:xs='$SchemaNamespace'>$body</xs:schema>"
    $selected = Select-XsdDeclaration $single ''
    Assert-Profile ($selected.GetAttribute('name') -ceq 'Only') "single_global_$($selected.LocalName)"
}
$empty = Read-NativeSchema "<xs:schema xmlns:xs='$SchemaNamespace'/>"
Assert-SelectionRejected $empty '' 'no_root_requires_selector'

$default = Read-NativeSchema @"
<schema xmlns="$SchemaNamespace" xmlns:t="$SchemaNamespace">
  <element name="Only" type="t:string"/>
</schema>
"@
$selected = Select-XsdDeclaration $default '/xs:schema/xs:element'
Assert-Profile ($selected.GetAttribute('name') -ceq 'Only') 'fixed_xs_binding_with_default_namespace'
Assert-SelectionRejected $default '/schema/element' 'xpath_default_namespace_not_inherited'

$prefix = Read-NativeSchema @"
<s:schema xmlns:s="$SchemaNamespace" xmlns:xs="urn:other">
  <s:element name="Only" type="s:string"/>
</s:schema>
"@
foreach ($expression in @('/s:schema/s:element', '/xs:schema/xs:element')) {
    $selected = Select-XsdDeclaration $prefix $expression
    Assert-Profile ($selected.GetAttribute('name') -ceq 'Only') "explicit_namespace_context_$expression"
}

$shadow = Read-NativeSchema @"
<xs:schema xmlns:xs="$SchemaNamespace" xmlns:s="$SchemaNamespace">
  <xs:element xmlns:s="urn:other" name="Only" type="xs:string"/>
</xs:schema>
"@
$selected = Select-XsdDeclaration $shadow '/s:schema/s:element'
Assert-Profile ($selected.GetAttribute('name') -ceq 'Only') 'descendant_namespace_does_not_rebind_expression'

$reference = Read-NativeSchema @"
<xs:schema xmlns:xs="$SchemaNamespace">
  <xs:element name="Root">
    <xs:complexType><xs:sequence><xs:element ref="Item"/></xs:sequence></xs:complexType>
  </xs:element>
  <xs:element name="Item" type="xs:string"/>
</xs:schema>
"@
Assert-SelectionRejected $reference "//xs:element[@ref='Item']" 'reference_node_is_not_a_declaration'
$selected = Select-XsdDeclaration $reference '//xs:complexType'
Assert-Profile ($selected.LocalName -ceq 'complexType') 'anonymous_type_definition_is_selectable'

foreach ($expression in @('/unknown:schema', '$unbound', "document('https://example.com/absent')")) {
    try {
        $null = Select-XsdDeclaration $document $expression
    }
    catch [System.Xml.XPath.XPathException] {
        Assert-Profile $true "unbound_xpath_facility_$expression"
        continue
    }
    throw "Expected an XPath context error: $expression"
}

try {
    $null = Read-NativeSchema @"
<xs:schema xmlns:xs="$SchemaNamespace">
  <xs:complexType name="Checked"><xs:assert test="true()"/></xs:complexType>
</xs:schema>
"@
}
catch [System.Xml.Schema.XmlSchemaException] {
    Assert-Profile $true 'native_runtime_is_xsd_1_0_not_xsd_1_1_validation'
    Write-Output "$script:Passed passed; XPath 1.0 and XSD 1.0 only; XSD 1.1 validation unsupported"
    exit 0
}
throw 'Expected the documented XSD 1.1 validation boundary'
