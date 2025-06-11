import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from confluent_kafka.cimpl import Message
from otteroad.models import RegionalScenarioCreated

from scenarios_conductor.handlers import RegionalScenarioCreatedHandler

REGIONAL_SCENARIO_CREATED_EVENTS_TOTAL = MagicMock()
REGIONAL_SCENARIO_CREATED_DURATION_SECONDS = MagicMock()
REGIONAL_SCENARIO_CREATED_SUCCESS_TOTAL = MagicMock()
REGIONAL_SCENARIO_CREATED_ERROR_TOTAL = MagicMock()


@pytest.mark.asyncio
class TestRegionalScenarioCreatedHandler:
    @pytest.fixture(autouse=True)
    def patch_metrics(self, monkeypatch):
        monkeypatch.setattr(
            "scenarios_conductor.handlers.regional_scenario_created.REGIONAL_SCENARIO_CREATED_EVENTS_TOTAL",
            REGIONAL_SCENARIO_CREATED_EVENTS_TOTAL,
        )
        monkeypatch.setattr(
            "scenarios_conductor.handlers.regional_scenario_created.REGIONAL_SCENARIO_CREATED_DURATION_SECONDS",
            REGIONAL_SCENARIO_CREATED_DURATION_SECONDS,
        )
        monkeypatch.setattr(
            "scenarios_conductor.handlers.regional_scenario_created.REGIONAL_SCENARIO_CREATED_SUCCESS_TOTAL",
            REGIONAL_SCENARIO_CREATED_SUCCESS_TOTAL,
        )
        monkeypatch.setattr(
            "scenarios_conductor.handlers.regional_scenario_created.REGIONAL_SCENARIO_CREATED_ERROR_TOTAL",
            REGIONAL_SCENARIO_CREATED_ERROR_TOTAL,
        )
        # Reset mocks before each test
        REGIONAL_SCENARIO_CREATED_EVENTS_TOTAL.reset_mock()
        REGIONAL_SCENARIO_CREATED_DURATION_SECONDS.reset_mock()
        REGIONAL_SCENARIO_CREATED_SUCCESS_TOTAL.reset_mock()
        REGIONAL_SCENARIO_CREATED_ERROR_TOTAL.reset_mock()
        yield

    @pytest.fixture
    def service(self):
        return AsyncMock()

    @pytest.fixture
    def logger(self):
        return AsyncMock()

    @pytest.fixture
    def handler(self, service, logger):
        return RegionalScenarioCreatedHandler(service=service, logger=logger)

    @pytest.fixture
    def event(self):
        return RegionalScenarioCreated(scenario_id=1, territory_id=23)

    @pytest.fixture
    def ctx(self):
        message = MagicMock(spec=Message)
        return message(topic="test", partition=0, offset=0, timestamp=None, timestamp_type=None, key=None, value=None)

    @pytest.mark.asyncio
    async def test_pre_process_increments_and_sets_time(self, handler, event, ctx):
        # Patch super().pre_process to just return inputs
        with patch.object(handler, "pre_process", wraps=handler.pre_process) as super_pre_process:
            # But we want to call original base pre_process after our code, so patch the parent's method directly
            # For simplicity, patch the base class method to just return inputs:
            base_pre_process = AsyncMock(return_value=(event, ctx))
            with patch(
                "scenarios_conductor.handlers.regional_scenario_created.BaseMessageHandler.pre_process",
                base_pre_process,
            ):
                result_event, result_ctx = await handler.pre_process(event, ctx)
                assert result_event == event
                assert result_ctx == ctx

        REGIONAL_SCENARIO_CREATED_EVENTS_TOTAL.inc.assert_called_once()
        assert "start_time" in handler._metadata
        assert isinstance(handler._metadata["start_time"], float)

    @pytest.mark.asyncio
    async def test_post_process_observes_duration_and_increments_success(self, handler):
        handler._metadata["start_time"] = time.perf_counter() - 0.1

        base_post_process = AsyncMock()
        with patch(
            "scenarios_conductor.handlers.regional_scenario_created.BaseMessageHandler.post_process", base_post_process
        ):
            await handler.post_process()

        REGIONAL_SCENARIO_CREATED_DURATION_SECONDS.observe.assert_called_once()
        REGIONAL_SCENARIO_CREATED_SUCCESS_TOTAL.inc.assert_called_once()
        assert "start_time" not in handler._metadata
        base_post_process.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_post_process_no_start_time(self, handler):
        # _metadata without start_time
        handler._metadata = {}

        base_post_process = AsyncMock()
        with patch(
            "scenarios_conductor.handlers.regional_scenario_created.BaseMessageHandler.post_process", base_post_process
        ):
            await handler.post_process()

        REGIONAL_SCENARIO_CREATED_DURATION_SECONDS.observe.assert_not_called()
        REGIONAL_SCENARIO_CREATED_SUCCESS_TOTAL.inc.assert_called_once()
        base_post_process.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_error_increments_error_and_calls_super(self, handler, event, ctx):
        error = Exception("fail")

        base_handle_error = AsyncMock()
        with patch(
            "scenarios_conductor.handlers.regional_scenario_created.BaseMessageHandler.handle_error", base_handle_error
        ):
            await handler.handle_error(error, event, ctx)

        REGIONAL_SCENARIO_CREATED_ERROR_TOTAL.inc.assert_called_once()
        base_handle_error.assert_awaited_once_with(error, event, ctx)

    @pytest.mark.asyncio
    async def test_handle_calls_service(self, handler, service, event, ctx):
        await handler.handle(event, ctx)
        service.handle_regional_scenario_created.assert_awaited_once_with(event)
