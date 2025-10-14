# Tasks: Finance Stocks Module - Stock Pack Builder & Modeling Framework

**Input**: Design documents from `/specs/001-en-as-the/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `hormax/` at repository root (Python package)
- Paths shown below use absolute references within hormax package

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project directory structure for hormax/finance/stocks/ with data_sources/, processors/, builders/, modeling/ subdirectories
- [ ] T002 Create all __init__.py files in hormax/finance/stocks/ and subdirectories for Python package structure
- [ ] T003 [P] Create hormax/exceptions.py with custom exception classes (StockPackError, FactorError, ConfigError, ValidationError, StockDataError)
- [ ] T004 [P] Create requirements.txt with dependencies (yfinance, pandas, openpyxl, pydantic, PyYAML, requests-cache, pytest, pytest-mock, freezegun)
- [ ] T005 [P] Create pyproject.toml with project metadata, dependencies, and build configuration
- [ ] T006 [P] Configure linting tools (.ruff.toml or setup.cfg with flake8, black line-length=100, isort profile=black)
- [ ] T007 [P] Create .gitignore for Python (.cache/, *.pyc, __pycache__/, .pytest_cache/, logs/, *.xlsx)
- [ ] T008 [P] Create config/ directory with example stock_pack.yaml and factor_requirements.yaml files
- [ ] T009 [P] Create logs/ directory with .gitkeep file
- [ ] T010 [P] Create tests/ directory structure (unit/, integration/, fixtures/, data/)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T011 Implement hormax/finance/stocks/entities.py with Ticker, DateRange, StockData, Returns, StockPack dataclasses
- [ ] T012 [P] Implement hormax/core/config.py with pydantic models (DataSourceConfig, CacheConfig, RateLimitConfig, StockPackConfig) and ConfigLoader class
- [ ] T013 [P] Implement hormax/core/logging_setup.py with setup_logging() function, RotatingFileHandler, and LoggerAdapter support
- [ ] T014 [P] Create test fixtures in tests/fixtures/conftest.py with sample Ticker, DateRange objects for testing
- [ ] T015 [P] Create sample test data in tests/data/sample_stock_data.csv with mock OHLCV data for 2-3 tickers
- [ ] T016 Implement hormax/finance/stocks/validators.py with input validation functions (validate_ticker_format, validate_date_range, validate_config)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Generate Stock Data Pack (Priority: P1) 🎯 MVP

**Goal**: Enable financial analysts to generate comprehensive Excel reports with stock data, returns, field documentation, and metadata

**Independent Test**: Provide tickers ["AAPL", "MSFT", "GOOGL"] and date range 2024-01-01 to 2024-12-31, verify output Excel file contains all 3 required sheets with correct data

### Implementation for User Story 1

#### Data Sources Layer (US1)

- [ ] T017 [P] [US1] Implement hormax/finance/stocks/data_sources/stock_data_source.py with StockDataSource class (init, fetch_price_history, fetch_metadata, validate_ticker methods using yfinance)
- [ ] T018 [P] [US1] Implement hormax/finance/stocks/data_sources/data_cache.py with DataCache class (init, get_cached, set_cached, is_expired methods using requests-cache)
- [ ] T019 [P] [US1] Implement hormax/finance/stocks/data_sources/rate_limiter.py with RateLimiter class (init, wait_if_needed, retry_with_backoff methods with exponential backoff)

#### Processors Layer (US1)

- [ ] T020 [P] [US1] Implement hormax/finance/stocks/processors/returns_calculator.py with ReturnsCalculator class (calculate_simple_return, calculate_log_return, validate_returns methods)
- [ ] T021 [P] [US1] Implement hormax/finance/stocks/processors/data_cleaner.py with DataCleaner class (fill_missing_dates, detect_gaps, validate_data_quality methods)

#### Builders Layer (US1)

- [ ] T022 [P] [US1] Implement hormax/finance/stocks/builders/field_dictionary.py with FieldDictionary class (get_standard_fields, generate_docs_dict static methods)
- [ ] T023 [US1] Implement hormax/finance/stocks/builders/excel_builder.py with ExcelBuilder class (init, add_field_dictionary_sheet, add_returns_sheet, add_metadata_sheet, add_hyperlink, save methods using openpyxl)

#### Orchestration Layer (US1)

- [ ] T024 [US1] Implement hormax/finance/stocks/stock_pack_builder.py with StockPackBuilder class (init, build, validate_inputs methods coordinating data fetch → returns calc → Excel generation)

#### Integration & Testing (US1)

- [ ] T025 [P] [US1] Create unit tests in tests/unit/test_stock_data_source.py with mocked yfinance API calls
- [ ] T026 [P] [US1] Create unit tests in tests/unit/test_returns_calculator.py with sample price series
- [ ] T027 [P] [US1] Create unit tests in tests/unit/test_excel_builder.py with mock workbook creation
- [ ] T028 [US1] Create integration test in tests/integration/test_stock_pack_builder.py with vcr.py cassette for real API recording
- [ ] T029 [US1] Validate US1: Generate demo stock pack for 3 tickers, verify Excel has Field Dictionary, Returns, and Metadata sheets with hyperlinks

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently (MVP complete!)

---

## Phase 4: User Story 2 - Configure and Apply Factor Models (Priority: P2)

**Goal**: Enable quantitative researchers to define custom factors, register them, and calculate per-ticker scores with configurable requirements

**Independent Test**: Define MomentumFactor (30-day returns), register it, configure requirements (price_history), generate scores for ["AAPL", "MSFT"]

### Implementation for User Story 2

#### Modeling Layer (US2)

- [ ] T030 [P] [US2] Implement hormax/finance/stocks/modeling/factor_interface.py with FactorInterface ABC (calculate, get_requirements abstract methods, name property)
- [ ] T031 [P] [US2] Implement hormax/finance/stocks/modeling/error_policies.py with ErrorPolicy Enum (SKIP, LOG, FAIL)
- [ ] T032 [US2] Implement hormax/finance/stocks/modeling/factor_registry.py with FactorRegistry class (register, get_factor, list_factors, validate_factor methods)
- [ ] T033 [US2] Implement hormax/finance/stocks/modeling/factor_runner.py with FactorRunner class (check_requirements, calculate_all, apply_error_policy methods)

#### Configuration & Validation (US2)

- [ ] T034 [US2] Extend hormax/core/config.py to add FactorRequirementsConfig pydantic model for factor_requirements.yaml schema validation
- [ ] T035 [US2] Implement circular dependency detection function in hormax/finance/stocks/modeling/factor_registry.py (detect_circular_deps using DFS)

#### Example Factors (US2)

- [ ] T036 [P] [US2] Create hormax/finance/stocks/modeling/examples/ directory with __init__.py
- [ ] T037 [P] [US2] Implement hormax/finance/stocks/modeling/examples/momentum_factor.py with MomentumFactor class implementing FactorInterface (30-day returns)
- [ ] T038 [P] [US2] Implement hormax/finance/stocks/modeling/examples/volatility_factor.py with VolatilityFactor class implementing FactorInterface (60-day std dev)

#### Integration & Testing (US2)

- [ ] T039 [P] [US2] Create unit tests in tests/unit/test_factor_registry.py with mock factor registration and validation
- [ ] T040 [P] [US2] Create unit tests in tests/unit/test_factor_runner.py with requirement checking and error policy testing
- [ ] T041 [US2] Create integration test in tests/integration/test_factor_modeling.py with full factor registration → calculation → output flow
- [ ] T042 [US2] Validate US2: Register MomentumFactor and VolatilityFactor, calculate scores for 5 tickers, verify CSV output with correct columns (ticker, factor, score, timestamp)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Handle Error Scenarios Gracefully (Priority: P3)

**Goal**: Ensure clear error handling, actionable messages, and graceful degradation for invalid inputs, API failures, and missing data

**Independent Test**: Provide invalid tickers, future dates, unavailable data; verify error messages are actionable and system continues processing valid data

### Implementation for User Story 3

#### Error Handling Enhancement (US3)

- [ ] T043 [P] [US3] Enhance hormax/exceptions.py with detailed error messages, context (ticker, date range, factor), and remediation suggestions
- [ ] T044 [US3] Add comprehensive error handling to hormax/finance/stocks/stock_data_source.py (handle 404, timeouts, rate limit errors with retries)
- [ ] T045 [US3] Add input validation edge cases to hormax/finance/stocks/validators.py (empty lists, single-day ranges, future dates, delisted tickers)
- [ ] T046 [US3] Implement error recovery in hormax/finance/stocks/stock_pack_builder.py (continue processing if some tickers fail, log all failures)

#### Edge Case Handling (US3)

- [ ] T047 [P] [US3] Add edge case handling to hormax/finance/stocks/processors/data_cleaner.py (weekends, holidays, IPO dates, delisting handling)
- [ ] T048 [P] [US3] Add Excel row limit detection to hormax/finance/stocks/builders/excel_builder.py (warn if data > 1,048,576 rows, suggest splitting)

#### Integration & Testing (US3)

- [ ] T049 [P] [US3] Create unit tests in tests/unit/test_validators.py for all edge cases (empty lists, invalid dates, malformed tickers)
- [ ] T050 [P] [US3] Create integration tests in tests/integration/test_error_scenarios.py with invalid tickers, future dates, API failures
- [ ] T051 [US3] Validate US3: Test with mix of valid/invalid tickers, verify system processes valid ones and logs actionable errors for invalid ones

**Checkpoint**: All user stories should now be independently functional with robust error handling

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and final deliverables

- [ ] T052 [P] Add type annotations to all public functions in hormax/finance/stocks/ ensuring mypy --strict compliance
- [ ] T053 [P] Add Google-style docstrings to all public APIs in hormax/finance/stocks/ (Args, Returns, Raises, Examples)
- [ ] T054 [P] Create CLI interface in hormax/finance/stocks/cli.py with commands: build (stock pack), factors (calculate scores), validate (tickers)
- [ ] T055 [P] Create example scripts in examples/ directory (generate_stock_pack.py, momentum_screening.py, multi_factor_analysis.py)
- [ ] T056 [P] Update CHANGELOG.md with new feature (Finance Stocks Module v1.0.0, added Stock Pack Builder and Factor Modeling)
- [ ] T057 [P] Create comprehensive unit tests for edge cases in tests/unit/ (1000+ tickers, 10-year ranges, concurrent access)
- [ ] T058 [US1] Run quickstart.md validation: Follow all examples in quickstart.md and verify they work without errors
- [ ] T059 Measure performance: Generate stock pack for 10 tickers over 1-year range, verify completion <60 seconds (excluding API latency)
- [ ] T060 Verify code coverage: Run pytest --cov=hormax.finance.stocks, ensure coverage >= 85%

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3, 4, 5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Integrates with US1 (uses stock data) but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Enhances error handling across US1/US2 but independently testable

### Within Each User Story

- **US1**: Data sources before processors, processors before builders, builders before orchestration
- **US2**: Factor interface before registry, registry before runner, runner before integration
- **US3**: Exception updates before implementations, implementations before tests

### Parallel Opportunities

- **Setup tasks** (T003-T010): All marked [P] can run in parallel
- **Foundational tasks** (T012-T015): All marked [P] can run in parallel
- **Within US1**:
  - T017, T018, T019 (data sources layer) can run in parallel
  - T020, T021 (processors layer) can run in parallel after data sources
  - T022 can run in parallel with T020/T021
  - T025, T026, T027 (unit tests) can run in parallel after implementations
- **Within US2**:
  - T030, T031 can run in parallel
  - T036, T037, T038 (example factors) can run in parallel after T030
  - T039, T040 (unit tests) can run in parallel after implementations
- **Within US3**:
  - T043, T047, T048 can run in parallel
  - T049, T050 (tests) can run in parallel after implementations
- **Polish tasks** (T052-T057): All marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch data sources layer together:
Task T017: "Implement stock_data_source.py with yfinance integration"
Task T018: "Implement data_cache.py with requests-cache"
Task T019: "Implement rate_limiter.py with exponential backoff"

# After data sources done, launch processors together:
Task T020: "Implement returns_calculator.py with simple/log returns"
Task T021: "Implement data_cleaner.py with gap handling"
Task T022: "Implement field_dictionary.py with field docs"

# After all implementations, launch unit tests together:
Task T025: "Unit tests for stock_data_source"
Task T026: "Unit tests for returns_calculator"
Task T027: "Unit tests for excel_builder"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T010)
2. Complete Phase 2: Foundational (T011-T016) - CRITICAL
3. Complete Phase 3: User Story 1 (T017-T029)
4. **STOP and VALIDATE**: Test US1 independently with quickstart examples
5. Deploy/demo MVP (Stock Pack Builder working!)

**MVP Deliverable**: Users can generate Excel stock packs with 3 sheets (field dictionary, returns, metadata), hyperlinks, and logging.

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (P1) → Test independently → Deploy/Demo **(MVP!)**
3. Add User Story 2 (P2) → Test independently → Deploy/Demo (Factor modeling added)
4. Add User Story 3 (P3) → Test independently → Deploy/Demo (Robust error handling)
5. Add Polish (Phase 6) → Final release

Each story adds value without breaking previous stories.

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (T017-T029)
   - Developer B: User Story 2 (T030-T042)
   - Developer C: User Story 3 (T043-T051)
3. Stories complete and integrate independently
4. Team completes Polish together

---

## Implementation Notes (per User Request)

### What Changed vs Plan

The tasks.md matches the plan.md architecture exactly. Key alignments:

1. **Architecture**: Preserved layered architecture (Data Sources → Processors → Builders → Modeling)
2. **Tech Stack**: All dependencies from plan.md included (yfinance, pandas, openpyxl, pydantic, etc.)
3. **Module Structure**: Exact file paths match plan.md structure (hormax/finance/stocks/ with subdirectories)
4. **Constitution Compliance**: All tasks follow constitution principles (modularity, type safety, YAML config, pytest testing)

**Trade-offs**:
- Tests are optional (not mandated by spec), but included as best practice for 85% coverage target
- CLI (T054) made optional in polish phase since spec says "library or CLI"
- Example factors (momentum, volatility) included for demonstration purposes

### Representative Code Snippets

**yfinance client** (T017 - stock_data_source.py):
```python
import yfinance as yf
from datetime import date

class StockDataSource:
    def fetch_price_history(self, ticker: Ticker, start_date: date, end_date: date) -> pd.DataFrame:
        """Fetch OHLCV data from yfinance."""
        try:
            data = yf.download(ticker.symbol, start=start_date, end=end_date, progress=False)
            if data.empty:
                raise StockDataError(ticker.symbol, "No data returned from API")
            return data.reset_index()  # Returns: date, open, high, low, close, volume, adj_close
        except Exception as e:
            logger.error(f"[{ticker.symbol}] Failed to fetch data: {e}")
            raise StockDataError(ticker.symbol, str(e))
```

**pack builder** (T024 - stock_pack_builder.py):
```python
class StockPackBuilder:
    def build(self, tickers: List[str], start_date: date, end_date: date, output_path: str) -> StockPack:
        """Orchestrate: fetch → process → build → output."""
        self.validate_inputs(tickers, start_date, end_date)

        all_data = {}
        for ticker_symbol in tickers:
            ticker = Ticker(ticker_symbol)
            try:
                # Fetch with caching & rate limiting
                df = self.data_source.fetch_price_history(ticker, start_date, end_date)
                all_data[ticker_symbol] = df
            except StockDataError as e:
                logger.error(f"Skipping {ticker_symbol}: {e}")
                continue

        # Calculate returns for all tickers
        returns_data = {}
        for symbol, df in all_data.items():
            returns_data[symbol] = self.returns_calc.calculate_simple_return(df["close"])

        # Build Excel with 3 sheets
        self.excel_builder.add_field_dictionary_sheet(FieldDictionary.generate_docs_dict())
        self.excel_builder.add_returns_sheet(pd.concat(returns_data), list(all_data.keys()))
        self.excel_builder.add_metadata_sheet(datetime.now(), {"tickers": tickers}, logs)
        self.excel_builder.save(output_path)

        return StockPack(tickers=[Ticker(s) for s in all_data.keys()], ...)
```

**factor compute** (T033 - factor_runner.py):
```python
class FactorRunner:
    def calculate_all(self, tickers: List[str], factors: List[FactorInterface], data: Dict) -> pd.DataFrame:
        """Calculate all factors for all tickers."""
        results = []
        for ticker_symbol in tickers:
            for factor in factors:
                # Check requirements
                available_fields = list(data[ticker_symbol].columns)
                if not self.check_requirements(factor, available_fields):
                    self.apply_error_policy(ticker_symbol, factor, MissingDataError(...))
                    continue

                # Calculate score
                try:
                    score = factor.calculate(data[ticker_symbol])
                    results.append({
                        "ticker": ticker_symbol,
                        "factor": factor.name,
                        "score": score,
                        "timestamp": datetime.now()
                    })
                except Exception as e:
                    self.apply_error_policy(ticker_symbol, factor, e)

        return pd.DataFrame(results)
```

### Test Strategy & Sample Tests

**Unit Test** (T025 - test_stock_data_source.py):
```python
def test_fetch_price_history(mocker):
    """Unit test with mocked yfinance API."""
    mock_download = mocker.patch("yfinance.download")
    mock_download.return_value = pd.DataFrame({
        "Close": [100, 101, 102],
        "Volume": [1000, 1100, 1200]
    })

    source = StockDataSource()
    ticker = Ticker("AAPL")
    df = source.fetch_price_history(ticker, date(2024,1,1), date(2024,1,3))

    assert len(df) == 3
    assert "Close" in df.columns
```

**Integration Test** (T028 - test_stock_pack_builder.py):
```python
@vcr.use_cassette("tests/fixtures/vcr_cassettes/aapl_msft_2024.yaml")
def test_build_stock_pack():
    """Integration test with recorded API responses."""
    builder = StockPackBuilder(config=default_config)
    pack = builder.build(
        tickers=["AAPL", "MSFT"],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        output_path="test_output.xlsx"
    )

    assert pack.success_rate() == 1.0  # Both tickers succeeded
    assert os.path.exists("test_output.xlsx")

    # Verify Excel has 3 sheets
    wb = openpyxl.load_workbook("test_output.xlsx")
    assert "Field Dictionary" in wb.sheetnames
    assert "Returns" in wb.sheetnames
    assert "Metadata & Logs" in wb.sheetnames
```

### How to Run Locally

```bash
# 1. Clone repo and navigate to hormax directory
cd /path/to/hormax

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run unit tests (fast, no network)
pytest tests/unit/ -v

# 4. Run integration tests (may hit network, use cached cassettes)
pytest tests/integration/ -v

# 5. Run all tests with coverage
pytest tests/ --cov=hormax.finance.stocks --cov-report=html

# 6. View coverage report
open htmlcov/index.html
```

### How to Generate a Demo Pack

```python
# demo.py
from hormax.finance.stocks import build_stock_pack
from datetime import date

# Generate stock pack for FAANG stocks
pack = build_stock_pack(
    tickers=["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
    start_date="2024-01-01",
    end_date="2024-12-31",
    output_path="demo_stock_pack.xlsx"
)

print(f"✓ Generated: {pack.excel_file_path}")
print(f"✓ Tickers: {len(pack.tickers)}")
print(f"✓ Success rate: {pack.success_rate():.1%}")
```

Run: `python demo.py`

Expected output:
```
INFO - Fetching data for AAPL...
INFO - Fetching data for MSFT...
INFO - Fetching data for GOOGL...
INFO - Fetching data for AMZN...
INFO - Fetching data for META...
INFO - Calculating returns...
INFO - Building Excel file...
INFO - Stock pack generated successfully!

✓ Generated: demo_stock_pack.xlsx
✓ Tickers: 5
✓ Success rate: 100.0%
```

### Known Limitations

1. **API Rate Limits**: yfinance free tier may throttle requests for large ticker lists (100+). Mitigation: T019 implements rate limiting + exponential backoff.
2. **Excel Row Limit**: Max 1,048,576 rows per sheet. For 10+ year ranges with many tickers, may exceed limit. Mitigation: T048 detects and warns users.
3. **No Database**: All data fetched on-demand from APIs, no local DB caching across sessions. Mitigation: T018 implements file-based HTTP cache (requests-cache).
4. **Alpha Vantage Support**: Planned but not prioritized in MVP. yfinance is primary data source.
5. **Factor Circular Dependencies**: Detection implemented (T035) but prevention relies on developer discipline.
6. **Concurrent Access**: No locking mechanism for cache writes. Multiple processes may have race conditions. Mitigation: Use separate cache directories per process.

### Next Steps (Post-Implementation)

1. **Performance Optimization**: Profile with 1000+ tickers, optimize pandas operations, add chunking for large requests
2. **Data Source Abstraction**: Implement adapter pattern to easily swap yfinance ↔ Alpha Vantage ↔ custom sources
3. **Web UI**: Build Flask/FastAPI web interface for non-technical users (currently CLI/library only)
4. **Real-Time Data**: Add WebSocket support for streaming live stock prices
5. **Advanced Factors**: Implement library of common factors (momentum, mean reversion, volatility, correlation, beta, etc.)
6. **Portfolio Analytics**: Extend to portfolio-level metrics (Sharpe ratio, max drawdown, correlation matrix)
7. **Backtesting**: Add backtesting framework for factor strategies
8. **Deployment**: Package as Docker container, deploy on cloud (AWS Lambda, GCP Cloud Run)

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
