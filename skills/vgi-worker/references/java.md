# Java

The published `farm.query:vgi:0.46.0` artifact requires Java 21+. Use the project's Gradle/Maven convention and pin the dependency. Pass `-parameters` to javac so the SDK can discover argument names.

```kotlin
implementation("farm.query:vgi:0.46.0")
```

Bake these runtime flags into the application start script:

```text
--add-opens=java.base/java.nio=org.apache.arrow.memory.core,ALL-UNNAMED
-Dio.netty.noUnsafe=false
--enable-native-access=ALL-UNNAMED
```

Use `Worker.builder().catalogName(...).registerScalar(...).runFromArgs(args)`. Build the distribution and test its start script through SQL. Use direct subprocesses during development; pooled launchers can continue serving an old build.

Emitted Arrow vectors transfer ownership. Do not close an emitted root or retain an input root the SDK reuses. Aggregate state must survive serialization and multiple batches.

Read the release examples:
- https://github.com/Query-farm/vgi-java/blob/v0.46.0/examples/docs/src/main/java/farm/query/vgi/examples/ScalarExample.java
- https://github.com/Query-farm/vgi-java/blob/v0.46.0/examples/docs/src/main/java/farm/query/vgi/examples/TableExample.java
- https://query.farm/vgi/docs/java/
