# Maliya — مالية

Le cockpit financier d'un entrepreneur qui gère plusieurs structures à la fois : une agence, une société, des projets et ses finances perso. L'IA tourne entièrement sur ta machine. Elle classe tes mouvements, prévoit ta trésorerie, repère ce qui cloche, explique pourquoi l'argent a bougé et répond à tes questions avec les vrais chiffres.

## Lancer en local

Il te faut Docker Desktop.

```bash
docker compose up --build
```

Puis ouvre **http://localhost:3000**.

Le premier lancement prend quelques minutes (téléchargement de Maven, PyTorch CPU et Node). Ensuite, ça démarre en une trentaine de secondes. Le service IA met environ 15 secondes à entraîner ses modèles au démarrage.

| Service | Adresse | Rôle |
|---|---|---|
| Interface React | http://localhost:3000 | ce que tu utilises |
| Backend Spring Boot | http://localhost:8080/api | grand livre, factures, projets, relais vers l'IA |
| Service IA FastAPI | http://localhost:8000/docs | modèles ML et deep learning, copilote |
| PostgreSQL 16 | localhost:5432 (maliya / maliya) | la base |

### Données de démo

La base démarre avec 18 mois de données fictives (environ 800 mouvements, 76 factures, 8 projets, 4 structures). Plusieurs histoires y sont cachées pour que l'IA ait de quoi travailler : un client qui paie de plus en plus tard, une facture AWS qui double, un freelance qui fait déraper un projet, un prélèvement en double, et une douzaine de mouvements pas encore classés.

Les données s'arrêtent au 15 octobre 2026, donc la « date du jour » est figée sur ce jour-là par défaut.

**Pour démarrer avec tes propres comptes**, copie `.env.exemple` en `.env` et mets :

```
MALIYA_AUJOURDHUI=
FLYWAY_LOCATIONS=classpath:db/migration
```

Lance ensuite `docker compose down -v` pour effacer la base de démo, puis `docker compose up`. Ajoute tes structures avec le bouton « + Ajouter » sous les intercalaires. Les prévisions et les analyses s'activent dès qu'il y a assez d'historique (environ 60 mouvements et quelques factures payées). La catégorisation et la saisie en langage naturel marchent dès le premier jour.

### LLM local (facultatif)

Le copilote répond déjà sans LLM : il comprend la question, interroge le grand livre et rédige la réponse lui-même. Un LLM local peut reformuler ces réponses plus naturellement, sans jamais toucher aux chiffres.

```bash
docker compose --profile llm up -d
docker compose exec ollama ollama pull qwen2.5:3b
```

Ensuite, dans `.env` : `OLLAMA_URL=http://ollama:11434`, puis `docker compose up -d ia`.

## Architecture

```
React (Vite)  ──/api──▶  Spring Boot  ──JDBC──▶  PostgreSQL
                              │                      ▲
                              └──/api/ia/*──▶  FastAPI (ML + PyTorch) ──lecture seule
                                                     │
                                               Ollama (optionnel)
```

- **Le front ne parle qu'au backend.** Tout ce qui commence par `/api/ia/` est relayé au service IA.
- **Écritures en JPA, lectures en SQL.** Les agrégats (tableau de bord, projets, grand livre) sont des requêtes SQL explicites, toutes rangées dans `backend/.../requetes/Requetes.java`.
- **L'IA lit la base en lecture seule** et se ré-entraîne toute seule quand les données changent.
- **Le LLM ne calcule jamais.** Les chiffres viennent toujours du grand livre. Le LLM, s'il est branché, ne fait que reformuler.

## L'IA, modèle par modèle

| Fonction | Technique | Fichier |
|---|---|---|
| Catégoriser un mouvement | TF-IDF sur n-grammes de caractères et régression logistique, avec un lexique français, darija et marques marocaines | `ai-service/app/modeles/categoriseur.py` |
| Prévoir la trésorerie sur 13 semaines | **LSTM (PyTorch)** à 2 couches sur les flux hebdomadaires, incertitude par Monte Carlo dropout (fourchette p10–p90) | `modeles/prevision.py` |
| Repérer les anomalies | **Isolation Forest et autoencodeur (PyTorch)**, scores combinés, avec des raisons lisibles (doublon, montant inhabituel, nouveau fournisseur) | `modeles/anomalies.py` |
| Prédire les retards de paiement | Gradient boosting (médiane et quantiles 20/80) sur l'historique de chaque client | `modeles/paiement.py` |
| Expliquer une variation (RCA) | Décomposition de l'écart par catégorie, puis par client ou fournisseur, avec les mouvements et factures en preuve | `analyses/rca.py` |
| Copilote | Classifieur d'intention (TF-IDF et régression logistique), règles prioritaires, extraction d'entités, un outil SQL par intention, LLM optionnel | `copilote/assistant.py` |
| Saisie en langage naturel | Montant, sens, date (« lbare7 », « hier »), projet et client par correspondance approchée, puis catégorie par le modèle | `analyses/saisie.py` |
| Jumeau financier | LSTM sur les premiers mois, puis moyenne sur 12 mois, et hypothèses (embauche, perte client, contrat, retards, dépense, rémunération) | `analyses/simulateur.py` |
| Relances | Brouillon dont le ton dépend du profil de paiement du client. Rien n'est envoyé automatiquement. | `main.py` |

Les métriques des modèles entraînés sont visibles sur `GET /api/ia/modeles`.

## Développer sans Docker

```bash
# 1. PostgreSQL : une base « maliya » (utilisateur maliya / maliya)

# 2. Backend (Java 21) — Flyway crée le schéma et charge la démo
cd backend && MALIYA_AUJOURDHUI=2026-10-15 mvn spring-boot:run

# 3. Service IA (Python 3.11+)
cd ai-service
pip install --index-url https://download.pytorch.org/whl/cpu torch
pip install -r requirements.txt
MALIYA_AUJOURDHUI=2026-10-15 uvicorn app.main:app --reload --port 8000

# 4. Front
cd frontend && npm install && npm run dev     # http://localhost:5173
```

Pour régénérer les données de démo : `python tools/generer_donnees_demo.py`.

## API du backend

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/structures` | intercalaires et soldes |
| POST | `/api/structures` | ajouter une structure et son compte |
| GET | `/api/tableau-de-bord?structureId=` | soldes, mois en cours, courbe 12 mois, postes, factures |
| GET | `/api/mouvements?structureId&q&categorieId&aClasser&page&taille` | grand livre |
| POST | `/api/mouvements` | nouveau mouvement (catégorisé par l'IA si aucune catégorie n'est donnée) |
| PATCH | `/api/mouvements/{id}` | corriger la catégorie ou le projet |
| POST | `/api/mouvements/valider-propositions` | accepter en bloc les propositions de l'IA |
| GET | `/api/factures?structureId&etat=OUVERTES\|PAYEES` | factures |
| POST | `/api/factures` | créer une facture (numéro automatique) |
| POST | `/api/factures/{id}/encaisser` | marquer payée et inscrire l'encaissement |
| GET | `/api/projets?structureId=` | budget, coût réel, marge, date d'épuisement du budget |
| GET/POST | `/api/ia/*` | relais vers le service IA (`briefing`, `prevision`, `anomalies`, `paiements`, `rca`, `copilote`, `simulation`, `saisie`, `relance`, `a-classer`, `modeles`) |

## Le design

Un classeur de comptable à Tanger : murs chaulés, encre indigo, bleu de Tanger, menthe pour les gains, grenade pour les pertes, safran pour ce qui demande ton attention. Chaque structure est un intercalaire qui dépasse de la page. Le grand livre est écrit sur des lignes de cahier Séyès. L'IA écrit à la main dans la marge rouge, comme un comptable qui annoterait ton cahier. Les polices (Schibsted Grotesk, Caveat, Reem Kufi) sont hébergées dans l'app, donc rien n'est chargé depuis l'extérieur.
