# Prediction Market Sentiment Engine - Implementation

## Phase 1: Config + Data Models
- [x] Add prediction config vars to `backend/app/config.py`
- [x] Create `backend/app/models/prediction.py` (PredictionRun, PredictionRunManager)

## Phase 2: Polymarket Client
- [x] Create `backend/app/services/polymarket_client.py`

## Phase 3: Scenario Generator
- [x] Create `backend/app/services/scenario_generator.py`

## Phase 4: Sentiment Analyzer
- [x] Create `backend/app/services/sentiment_analyzer.py`

## Phase 5: Pipeline Orchestrator
- [x] Create `backend/app/services/prediction_manager.py`

## Phase 6: API Endpoints
- [x] Create `backend/app/api/prediction.py`
- [x] Register blueprint in `backend/app/api/__init__.py`
- [x] Register blueprint in `backend/app/__init__.py`

## Phase 7: Frontend
- [x] Create `frontend/src/api/prediction.js`
- [x] Create `frontend/src/views/PredictionView.vue`
- [x] Add route in `frontend/src/router/index.js`
- [x] Add nav link in `frontend/src/views/Home.vue`

## Verification
- [x] All Python files pass syntax check
- [ ] Backend starts without errors (needs virtualenv)
- [ ] GET /api/prediction/markets returns data
- [ ] POST /api/prediction/run starts pipeline
- [ ] Frontend renders and navigates correctly
