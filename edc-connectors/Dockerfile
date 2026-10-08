FROM gradle:9.7.1-jdk21 AS build

WORKDIR /src
COPY edc-connectors/edc-runtime/ ./
RUN gradle --no-daemon \
    :transfer:transfer-00-prerequisites:connector:shadowJar \
    :transfer:transfer-03-consumer-pull:provider-proxy-data-plane:shadowJar

FROM eclipse-temurin:21-jre
ARG CONNECTOR_MODULE=transfer/transfer-03-consumer-pull/provider-proxy-data-plane
WORKDIR /app
COPY --from=build /src/${CONNECTOR_MODULE}/build/libs/connector.jar /app/connector.jar
EXPOSE 8181 8184 8185
ENTRYPOINT ["java"]
