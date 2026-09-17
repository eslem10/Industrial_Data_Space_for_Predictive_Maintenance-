# Eclipse Dataspace Connector setup

This directory contains the Eclipse Dataspace Connector (EDC) setup added for the
predictive-maintenance project. It defines a small provider/consumer data-space
example using EDC `0.18.0`.

## What was added

- A Gradle project for building an EDC connector runtime.
- EDC control-plane and data-plane base dependencies.
- Filesystem configuration and mock IAM support for local development.
- A **provider** configuration using participant ID `provider`.
- A **consumer** configuration using participant ID `consumer`.
- Separate HTTP port ranges for the provider (`19191`-`19197`) and consumer
  (`29191`-`29197`) so both runtimes can run locally at the same time.
- `asset.json`, which describes the sample predictive-maintenance weights file
  (`provider/sample-weights.txt`) as a text asset.
- Gradle wrapper scripts so the project can be built without a system Gradle
  installation.

## Project structure

```text
edc_connector/
├── asset.json
├── connector/
│   └── build.gradle.kts
├── consumer/
│   └── config.properties
├── provider/
│   ├── config.properties
│   └── sample-weights.txt
├── gradle/
│   └── libs.versions.toml
├── gradlew
└── settings.gradle.kts
```

## Building

From this directory, run:

```powershell
.\gradlew.bat build
```

The shaded connector JAR is generated as:

```text
connector/build/libs/connector.jar
```

## Running locally

The provider and consumer configurations are intended to be used by separate
EDC runtime processes. Start each runtime with its corresponding configuration
file:

```powershell
.\gradlew.bat :connector:shadowJar
java -Dedc.fs.config=provider/config.properties -jar connector/build/libs/connector.jar
java -Dedc.fs.config=consumer/config.properties -jar connector/build/libs/connector.jar
```

The exact configuration property used to select a file depends on the EDC
runtime launch setup. The provider and consumer files expose the configured
ports and callback addresses for local integration.

## Asset note

`asset.json` currently contains an absolute Windows path to
`provider/sample-weights.txt`. Update the `dataAddress.path` value if the
repository is cloned to a different location or run on another operating
system.
