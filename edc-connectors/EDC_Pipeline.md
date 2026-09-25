# Industrial Data Space — EDC Pipeline (Personne 3)

**Projet :** Industrial Data Space for Predictive Maintenance — federated learning entre 3 usines
**Rôle :** Data Space & connecteurs EDC (Eclipse Dataspace Components)
**Statut :** Connecteur EDC de référence (provider/consumer) validé de bout en bout — publier, découvrir, négocier et transférer fonctionnent.

---

## Phase 0 — Consolider l'acquis (à faire en premier)

- [ ] Documenter la config finale qui fonctionne dans un README de `edc_connector/` : `build.gradle.kts` final, les deux `config.properties`, les deux fichiers d'extension Java, et la séquence curl complète.
- [ ] Automatiser la séquence manuelle (policy → asset → contractdef → catalogue → négociation → transfert) dans un script PowerShell ou Python, puisque les stores en mémoire s'effacent à chaque redémarrage.

### Configuration finale qui fonctionne

**`connector/build.gradle.kts`** (dépendances clés) :
```kotlin
dependencies {
    runtimeOnly(libs.edc.bom.controlplane.base) {
        exclude(group = "org.eclipse.edc", module = "data-plane-signaling-core")
        exclude(group = "org.eclipse.edc", module = "data-plane-signaling-oauth2")
    }
    implementation(libs.edc.control.plane.api.client)
    implementation(libs.edc.iam.mock)
    implementation(libs.edc.transfer.data.plane.signaling)
    implementation(libs.edc.validator.data.address.http.data)
    implementation(libs.edc.configuration.filesystem)

    implementation(libs.edc.edr.cache.api)
    implementation(libs.edc.edr.store.core)
    implementation(libs.edc.edr.store.receiver)

    implementation(libs.edc.data.plane.self.registration)
    implementation(libs.edc.data.plane.signaling.api)
    implementation(libs.edc.data.plane.signaling.client)
    implementation(libs.edc.data.plane.core)
    implementation(libs.edc.data.plane.http)
    implementation(libs.edc.data.plane.iam)

    implementation(libs.edc.data.plane.spi)
    implementation(libs.edc.web.spi)
}
```

**Extension Java custom** (mode PULL — `connector/src/main/java/org/eclipse/edc/sample/extension/proxy/`) :
- `CustomProxyDataPlaneExtension.java` — enregistre le générateur d'endpoint public pour le type `HttpData`
- `ProxyController.java` — sert de proxy authentifié entre le consumer et la source de données
- Déclarées dans `META-INF/services/org.eclipse.edc.spi.system.ServiceExtension`
- ⚠️ Créer ces fichiers avec `-Encoding ASCII` en PowerShell, jamais `UTF8` (ajoute un BOM que `javac` refuse)

**Clés de config essentielles** (les deux côtés, ports différenciés provider 191xx / consumer 291xx) :
```properties
edc.participant.id=provider
edc.dsp.callback.address=http://localhost:19194/protocol
web.http.port=19191
web.http.path=/api
web.http.control.port=19192
web.http.control.path=/control
web.http.management.port=19193
web.http.management.path=/management
web.http.protocol.port=19194
web.http.protocol.path=/protocol
web.http.public.port=19291
web.http.public.path=/public
web.http.validation.port=19195
web.http.validation.path=/validation
web.http.data.port=19196
web.http.data.path=/api/v1/data
web.http.signaling.port=19197
web.http.signaling.path=/signaling
edc.dataplane.api.public.baseurl=http://localhost:19291/public
edc.dataplane.proxy.public.endpoint=http://localhost:19291/public
edc.transfer.proxy.token.signer.privatekey.alias=1
edc.transfer.proxy.token.verifier.publickey.alias=public-key
```

**Protocole DSP** : `dataspace-protocol-http:2025-1` (pas juste `dataspace-protocol-http`), adresses avec suffixe `/protocol/2025-1`.

---

## Phase 1 — Clore la semaine 1 (jour 5)

- [ ] Rédiger la note de conception (2-3 paragraphes) : architecture des 3 providers + 1 consumer, policies prévues, format d'asset `poids-usine{N}-round{K}`
- [ ] Mentionner brièvement les vraies difficultés rencontrées (modules manquants des BOMs, générateur d'endpoint PULL absent du framework) — bon matériau pour le rapport, ça montre un vrai travail d'ingénierie
- [ ] Intégrer au document d'architecture commun de l'équipe

---

## Phase 2 — Semaine 2 : passer à l'échelle du vrai cas d'usage

1. **Renommage aligné sur le dashboard** : `EDC-F1-PROD`, `EDC-F2-PROD`, `EDC-F3-PROD` (usines), nom à définir pour le connecteur central (ex. `EDC-FEDERATION-SERVER`)
2. **Dupliquer la config en 4 dossiers** : `usine1/`, `usine2/`, `usine3/`, `federation-server/` — même jar, plages de ports différentes (19xxx/39xxx/49xxx/59xxx), chacun avec son propre `edc.dataplane.proxy.public.endpoint`
3. **Format réel des poids** avec la Personne 2 — remplacer `sample-weights.txt` par le vrai fichier produit par son script (`.h5`/`.npz`/`.keras`)
4. **Un asset par usine par round**, convention `poids-usine{N}-round{K}`
5. **Script Python d'automatisation** : après chaque round local, le script de la Personne 2 appelle `requests.post()` pour créer/mettre à jour l'asset du round
6. **Test de bout en bout** : round simulé → asset publié → négociation → transfert → vérification du fichier reçu

---

## Phase 3 — Semaine 3 : boucle FedAvg complète + Kubernetes

1. Avec la Personne 2 : brancher le vrai cycle — chaque round, les 3 usines publient, le serveur central négocie avec chacune, récupère les 3 fichiers, agrège
2. Gérer les échecs de négociation / timeouts (polling du statut avant transfert)
3. **Dockerfile** par connecteur (image Java + `connector.jar`), config externalisée via variables d'environnement / ConfigMap Kubernetes
4. **Manifests Kubernetes** : un Deployment + Service par connecteur (3 usines + 1 central)
5. Déploiement sur Minikube/Kind, vérification de la communication inter-pods, réexécution du flux complet sur le cluster

---

## Phase 4 — Semaine 4 : fiabilisation, traçabilité, rapport

1. Gestion d'erreurs (connecteur indisponible, négociation refusée, timeout) avec logs clairs
2. Vérifications anti-doublon (round déjà transféré)
3. Export de traçabilité : logs de négociation/transfert, `ContractAgreement` en JSON pour la soutenance
4. Endpoint d'état pour remplacer les valeurs hardcodées d'`EDCStatus.jsx` côté dashboard (Personne 4)
5. Rédaction de la section rapport : choix d'architecture, policies, preuve de traçabilité, difficultés rencontrées
6. Répétition de la démo live (publication → négociation → transfert visible en direct)

---

## Prochaine action immédiate

Écrire le script d'automatisation de la Phase 0 avant d'attaquer la Phase 1 — il fera gagner énormément de temps dès la Phase 2, quand la séquence devra tourner sur 4 connecteurs au lieu de 2.
