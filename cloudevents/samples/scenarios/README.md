# xRegistry Sample Overview

This document explains the various .xreg.json files in this directory. These
files model different use cases using the [xRegistry
specification](../../../core/spec.md). As described in the [xRegistry
Primer](../../../core/primer.md), a common metadata model underpins all
configurations to enable interoperability, versioning, and schema validation.

## Overview

- xRegistry centralizes event metadata definitions and resource descriptions.
- Each sample file uses the CloudEvents envelope and provides a vendor-agnostic
  representation of event schemas.

## Samples Details

### Watchkam

The Watchkam sample models security camera events using a CloudEvents envelope
to capture motion detection and motion end events with detailed analytics
defined using JSON Schema Draft-07.
[watchkam-jsons07.xreg.json](./watchkam-jsons07.xreg.json).

### Vacuumcleaner

The Vacuumcleaner sample demonstrates operational events for a robotic vacuum
using Avro 1.11 schemas to define lifecycle events such as cleaning start/stop,
docking, and error handling.
[vacuumcleaner-avro.xreg.json](./vacuumcleaner-avro.xreg.json).

### Smartoven

The Smartoven sample captures state changes for a smart oven with XML Schema 1.1
definitions that cover events like turning on/off, timer settings, and
preheating operations. [smartoven-xsd.xreg.json](./smartoven-xsd.xreg.json).

### Inkjet

The Inkjet sample provides a schema for an inkjet printer using Protobuf/3 to
define high-performance, type-safe event data for operations including print job
management and maintenance alerts.
[inkjet-proto3.xreg.json](./inkjet-proto3.xreg.json).

### Lightbulb

The Lightbulb sample defines events for a smart lightbulb using Avro 1.11
schemas to monitor energy usage and report status changes such as brightness and
color adjustments. [lightbulb-avro.xreg.json](./lightbulb-avro.xreg.json).

### Contoso ERP

The Contoso ERP sample demonstrates a complex registry for an ERP system,
integrating diverse domains and multiple schema types (e.g., JSON Schema
Draft-07) to cover events across reservations, payments, inventory, and more.
[contoso-erp-jsons07.xreg.json](./contoso-erp-jsons07.xreg.json).

### Water Boiler

The Water Boiler sample models water boiler events using MQTT/5.0, where the
topic encodes context and JSON Schema Draft-07 defines events like temperature
updates and status changes.
[waterboiler-mqtt5-jsons07.xreg.json](./waterboiler-mqtt5-jsons07.xreg.json).

### Wind Generator

The Wind Generator sample models wind generator events using Kafka with
Avro/1.11 schemas to define events such as power output updates and status
changes, embedding context in headers and key.
[windgenerator-kafka-avro.xreg.json](./windgenerator-kafka-avro.xreg.json).

## Conclusion

Each sample file not only encapsulates a focused area of an event-driven system
but also demonstrates the use of different schema technologies. This variation —
from JSON Schema Draft-07 to Avro, XML Schema 1.1, and Protobuf/3 — highlights
xRegistry’s flexibility in accommodating diverse metadata requirements and
industry standards. For further details, refer to the [xRegistry
Primer](../../../core/primer.md) which provides an in-depth explanation of the
design goals and benefits of this approach.

