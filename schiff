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

#    ema = qtpylib.rolling_weighted_mean(
#        series=pd.Series(index=dataframe.index, data=dataframe["ema"]), window=timeperiod
#    )

#    ema = qtpylib.rolling_weighted_mean(
#         series=pd.Series(index=dataframe.index), window=13
#    )

    ema = ta.EMA(dataframe, timeperiod=tpe, window=timeperiod)

    barshigh = (dataframe["high"])

    low = qtpylib.rolling_mean(
        series=pd.Series(index=dataframe.index, data=dataframe["low"]), window=timeperiod
    )

    high = qtpylib.rolling_mean(
        series=pd.Series(index=dataframe.index, data=dataframe["high"]), window=timeperiod
    )

    # Pivot
#    data["pivot"] = qtpylib.rolling_mean((high + ema) / 2)
    data["pivot"] = qtpylib.rolling_mean(series=typical_schiff(dataframe), window=timeperiod)
#    data["pivot"] = qtpylib.rolling_mean((high + ema) / 2)

    # Resistance #1
    # data["r1"] = (2 * data["pivot"]) - low ... Standard
    # R1 = PP + 0.382 * (HIGHprev - LOWprev) ... fibonacci
    data["r1"] = data['pivot'] + 0.382 * (high - low)

    # Resistance #2
    # data["s1"] = (2 * data["pivot"]) - high ... Standard
    # S1 = PP - 0.382 * (HIGHprev - LOWprev) ... fibonacci
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
