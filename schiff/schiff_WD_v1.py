# --- Do not remove these libs ---
from freqtrade.strategy import IStrategy, merge_informative_pair
from pandas import DataFrame
import talib.abstract as ta
import logging
import freqtrade.vendor.qtpylib.indicators as qtpylib
from technical.indicators import PMAX, zema
import math


# --------------------------------
import pandas as pd
import numpy as np
import technical.indicators as ftt
from freqtrade.exchange import timeframe_to_minutes
from technical.util import resample_to_interval, resampled_merge
from pandas.core.base import PandasObject


logger = logging.getLogger(__name__)


def typical_schiff(bars, timeperiod=88):

    ema = ta.EMA(bars, timeperiod=timeperiod)
    typical = bars['high']
    res = (typical + ema) / 2
    return pd.Series(index=bars.index, data=res)



def pivots_points(dataframe: pd.DataFrame, tpe=100, timeperiod=1, levels=3) -> pd.DataFrame:
    """
    Pivots Points
    https://www.tradingview.com/support/solutions/43000521824-pivot-points-standard/
    Formula:
    Pivot = (Previous High + Previous Low + Previous Close)/3
    Resistance #1 = (2 x Pivot) - Previous Low
    Support #1 = (2 x Pivot) - Previous High
    Resistance #2 = (Pivot - Support #1) + Resistance #1
    Support #2 = Pivot - (Resistance #1 - Support #1)
    Resistance #3 = (Pivot - Support #2) + Resistance #2
    Support #3 = Pivot - (Resistance #2 - Support #2)
    ...
    :param dataframe:
    :param timeperiod: Period to compare (in ticker)
    :param levels: Num of support/resistance desired
    :return: dataframe
    """

    data = {}

    low = qtpylib.rolling_mean(
        series=pd.Series(index=dataframe.index, data=dataframe["low"]), window=timeperiod
    )

    high = qtpylib.rolling_mean(
        series=pd.Series(index=dataframe.index, data=dataframe["high"]), window=timeperiod
    )

    # Pivot
    data["pivot"] = qtpylib.rolling_mean(series=typical_schiff(dataframe), window=timeperiod)

    data["r1"] = data['pivot'] + 0.382 * (high - low)

    data["s1"] = data["pivot"] - 0.382 * (high - low)

    # Calculate Resistances and Supports >1
    for i in range(2, levels + 1):
        prev_support = data["s" + str(i - 1)]
        prev_resistance = data["r" + str(i - 1)]

        # Resitance
        data["r" + str(i)] = (data["pivot"] - prev_support) + prev_resistance

        # Support
        data["s" + str(i)] = data["pivot"] - (prev_resistance - prev_support)

    return pd.DataFrame(index=dataframe.index, data=data)


class schiff_WD_v1(IStrategy):
    # La Estrategia es: schiff_WD_v1, velas high_1W a ema88_1d
    # Origen: schiff_v4

    # Optimal timeframe for the strategy
    timeframe = '15m'

    # generate signals from the 1h timeframe
    informative_timeframe = '1w'

    # WARNING: ichimoku is a long indicator, if you remove or use a
    # shorter startup_candle_count your results will be unstable/invalid
    # for up to a week from the start of your backtest or dry/live run
    # (180 candles = 7.5 days)
    startup_candle_count = 444  # MAXIMUM ICHIMOKU

    # NOTE: this strat only uses candle information, so processing between
    # new candles is a waste of resources as nothing will change
    process_only_new_candles = True

    minimal_roi = {
        "0": 10,
    }
    
    plot_config = {
        'main_plot': {
            'pivot_1d': {},
            'r1_1d': {},
            's1_1d': {},
        },
        'subplots': {
            'MACD': {
                'macd_1h': {'color': 'blue'},
                'macdsignal_1h': {'color': 'orange'},
            },
        }
    }

    # WARNING setting a stoploss for this strategy doesn't make much sense, as it will buy
    # back into the trend at the next available opportunity, unless the trend has ended,
    # in which case it would sell anyway.

    # Stoploss:
    stoploss = -0.10

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative_pairs = [(pair, self.informative_timeframe)
                             for pair in pairs]
        if self.dp:
            for pair in pairs:
                informative_pairs += [(pair, "1d"),(pair, "1w")]

        return informative_pairs

    def slow_tf_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        # Pares en "1d"
        dataframe1d = self.dp.get_pair_dataframe(
            pair=metadata['pair'], timeframe="1d")

        dataframe1d['ema88'] = ta.EMA(dataframe1d, timeperiod=88)

        dataframe = merge_informative_pair(
            dataframe, dataframe1d, self.timeframe, "1d", ffill=True)
        
        # Pares en "1w"
        dataframe1w = self.dp.get_pair_dataframe(
            pair=metadata['pair'], timeframe="1w")

        dataframe1w['ema88'] = ta.EMA(dataframe1w, timeperiod=88)

        # Pivots Points
        pp = pivots_points(dataframe1w)
        dataframe1w['pivot'] = pp['pivot']
        dataframe1w['r1'] = pp['r1']
        dataframe1w['s1'] = pp['s1']

        dataframe = merge_informative_pair(
            dataframe, dataframe1w, self.timeframe, "1w", ffill=True)

        # dataframe normal

        dataframe['ema20'] = ta.EMA(dataframe, timeperiod=20)

        dataframe['T3_33'] = ta.T3(dataframe, timeperiod=33)


        # NOTE: Start Trading

        dataframe['trending_start'] = (
            (dataframe['close'] > dataframe['pivot_1w']) &
            (dataframe['r1_1w'] > dataframe['close'])

        ).astype('int')        

        dataframe['trending_over'] = (
            (
            (dataframe['high'] > dataframe['r1_1w'])
            )
            |
            (
            (dataframe['pivot_1w'] > dataframe['close'])   
            )
        ).astype('int')

        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        dataframe = self.slow_tf_indicators(dataframe, metadata)

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        dataframe.loc[
            (
                (dataframe['trending_start'] > 0)
            ), 'buy'] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['trending_over'] > 0)
            ), 'sell'] = 1
        return dataframe
