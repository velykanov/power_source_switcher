import asyncio
from unittest import mock

import freezegun
import pytest

from main import Controller, Source


@pytest.fixture
def controller():
    return Controller()


@pytest.mark.parametrize(
    'source, current_time, is_time_to_switch',
    (
        (Source.SECONDARY, '20:00', False),
        (Source.GRID, '02:00', False),
        (Source.SECONDARY, '23:00', False),
        (Source.SECONDARY, '23:01:01', True),
        (Source.GRID, '06:59:01', True),
    ),
)
@pytest.mark.asyncio
async def test_is_time_to_switch(controller, source, current_time, is_time_to_switch):
    controller.source = source
    with freezegun.freeze_time(current_time):
        assert await controller.is_time_to_switch is is_time_to_switch


@pytest.mark.parametrize(
    'source, expected_source',
    (
        (Source.SECONDARY, Source.GRID),
        (Source.GRID, Source.SECONDARY),
    ),
    ids=('Secondary -> Grid', 'Grid -> Secondary'),
)
@pytest.mark.asyncio
async def test_switch_source(controller, source, expected_source):
    controller.source = source
    await controller.switch_source()

    # wait for 6 seconds to ensure debounce is skipped
    await asyncio.sleep(6)
    assert controller.source == expected_source


@pytest.mark.asyncio
async def test_switch_source_cancelled(controller):
    controller.source = Source.GRID
    await controller.switch_source()
    await asyncio.sleep(2)
    await controller.switch_source()
    await asyncio.sleep(4)
    assert controller.source == Source.GRID


@pytest.mark.asyncio
async def test_do_switch_source(controller):
    controller.source = Source.GRID
    with mock.patch('main.GPIO') as mock_gpio:
        await controller._do_switch_source()

    assert controller.source == Source.SECONDARY
    assert mock_gpio.output.call_count == 2
    mock_gpio.output.assert_has_calls([
        mock.call(23, mock_gpio.LOW),
        mock.call(24, mock_gpio.HIGH),
    ])
