# Script test safety

Live Neo4j sections are disabled unless `RUN_LIVE_NEO4J_TESTS=1` and the dedicated `NEO4J_TEST_URI`, `NEO4J_TEST_USERNAME`, and `NEO4J_TEST_PASSWORD` variables are set. Tests never fall back to the application's `NEO4J_URL`; absent or incomplete test configuration is reported as deferred. All live tests, including read-only graph-wide scans, refuse Railway endpoints and the endpoint configured as application `NEO4J_URL`.

Any write or idempotency test additionally requires `NEO4J_TEST_TARGET_MARKER=DISPOSABLE_TEST_ONLY` and `NEO4J_TEST_DISPOSABLE_ACK=I_ACKNOWLEDGE_THIS_IS_A_DISPOSABLE_NEO4J_TEST_DATABASE`. Use a separately provisioned disposable database.
