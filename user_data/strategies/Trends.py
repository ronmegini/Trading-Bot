import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame

from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IStrategy, IntParameter)
import freqtrade.vendor.qtpylib.indicators as qtpylib

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import pandas_ta as pta
import freqtrade.vendor.qtpylib.indicators as qtpylib
#For Numerical Differentiation Pivot Points
from findiff import FinDiff

class Trends(IStrategy):
    INTERFACE_VERSION = 2
    timeframe = '1h'
    minimal_roi = {
        "60": 0.01,
        "30": 0.02,
        "0": 0.04
    }
    stoploss = -0.10
    trailing_stop = False
    process_only_new_candles = False
    use_sell_signal = True
    sell_profit_only = False
    ignore_roi_if_buy_signal = False
    startup_candle_count: int = 30
    buy_rsi = IntParameter(10, 40, default=30, space="buy")
    sell_rsi = IntParameter(60, 90, default=70, space="sell")

    order_types = {
        'buy': 'limit',
        'sell': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    order_time_in_force = {
        'buy': 'gtc',
        'sell': 'gtc'
    }
    
    @property
    def plot_config(self):
        return {
            # Main plot indicators (Moving averages, ...)
            'main_plot': {
                'tema': {},
                'sar': {'columeumeor': 'white'},
            },
            'subplots': {
                # Subplots - each dict defines one additional plot
                "MACD": {
                    'macd': {'columeumeor': 'blue'},
                    'macdsignal': {'columeumeor': 'orange'},
                },
                "RSI": {
                    'rsi': {'columeumeor': 'red'},
                }
            }
        }
 
    def informative_pairs(self):
        """
        Define additional, informative pair/interval combinations to be cached from the exchange.
        These pair/interval combinations are non-tradeable, unless they are part
        of the whitelist as well.
        For more information, please consult the documentation
        :return: List of tuples in the format (pair, interval)
            Sample: return [("ETH/USDT", "5m"),
                            ("BTC/USDT", "15m"),
                            ]
        """
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds several different TA indicators to the given DataFrame

        Performance Note: For the best performance be frugal on the number of indicators
        you are using. Let uncomment only the indicator you are using in your strategies
        or your hyperopt configuration, otherwise you will waste your memory and CPU usage.
        :param dataframe: Dataframe with data from the exchange
        :param metadata: Additional information, like the currently traded pair
        :return: a Dataframe with all mandatory indicators for the strategies
        """

        #Default indicators
        dataframe['rsi'] = ta.RSI(dataframe)
        dataframe['tema'] = ta.TEMA(dataframe, timeperiod=9)
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_middleband'] = bollinger['mid']
        
        #stupid pivot points
        """
        pp = self.pivots_points(dataframe)
        self.naive_pivot_points(dataframe)
        dataframe['r1'] = pp["r1"]
        dataframe['s1'] = pp["s1"]
        dataframe['pivot'] = pp["pivot"]
        """
        
        # naive pivot points
        """
        naive_min_max = self.naive_pivot_points
        dataframe["min"] = naive_min_max["minimaIdxs"]
        dataframe["max"] = naive_min_max["maximaIdxs"]
        """
        
        #consecutive duplicates pivot points
        consecutive_duplicates_min_max = self.consecutive_duplicates_pivot_points(dataframe)
        dataframe["min"] = consecutive_duplicates_min_max["minimaIdxs"]
        dataframe["max"] = consecutive_duplicates_min_max["maximaIdxs"]
        
        
        """
        #momentum and acceleration of the price
        mom_and_acc = self.mom_and_momacc(dataframe)
        dataframe["mom"] = mom_and_acc["mom"]
        dataframe["momacc"] = mom_and_acc["momacc"]

        #min and max points based on differential calculation
        diff_min_and_max = self.differential_pivot_points(dataframe)
        dataframe["diff_min"] = diff_min_and_max["diff_min"]
        dataframe["diff_max"] = diff_min_and_max["diff_max"]
        """
        #print dataframe content
        print("############## DATAFRAME ################")
        #pd.set_option('display.max_rows', dataframe.shape[0]+1)
        dataframe.style.hide(["rsi", "tema", "bb_middleband"],axis=1)
        print(dataframe)
        print("#########################################")
        
        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the buy signal for the given dataframe
        :param dataframe: DataFrame populated with indicators
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with buy columeumeumn
        """
        dataframe.loc[
            (
                (dataframe["min"] == 1.0)
            ),
            'buy'] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the sell signal for the given dataframe
        :param dataframe: DataFrame populated with indicators
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with buy columeumeumn
        """
        dataframe.loc[
            (
                (dataframe["max"] == 1.0)
            ),
            'sell'] = 1
        return dataframe

    def stupid_pivots_points(self, dataframe, timeperiod=2, levels=3) -> DataFrame:
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
        low = qtpylib.rolling_mean(series=pd.Series(index=dataframe.index, data=dataframe["low"]), window=timeperiod)
        high = qtpylib.rolling_mean(series=pd.Series(index=dataframe.index, data=dataframe["high"]), window=timeperiod)
        # Pivot
        data["pivot"] = qtpylib.rolling_mean(series=qtpylib.typical_price(dataframe), window=timeperiod)
        # Resistance #1
        data["r1"] = (2 * data["pivot"]) - low
        # Resistance #2
        data["s1"] = (2 * data["pivot"]) - high

        # Calculate Resistances and Supports >1
        for i in range(2, levels + 1):
            prev_support = data["s" + str(i - 1)]
            prev_resistance = data["r" + str(i - 1)]
            # Resitance
            data["r" + str(i)] = (data["pivot"] - prev_support) + prev_resistance
            # Support
            data["s" + str(i)] = data["pivot"] - (prev_resistance - prev_support)

        return pd.DataFrame(index=dataframe.index, data=data)
    
    def naive_pivot_points(self, dataframe) -> DataFrame:
        """
        Naive Pivots Points:
        https://towardsdatascience.com/programmatic-identification-of-support-resistance-trend-lines-with-python-d797a4a90530
        Formula:
        Caluculate pivot points based on rolling window when the middle candle
        is lower or higher then the others.
        ...
        :param dataframe:
        :return: dataframe
        """
        data = {}
        minimaIdxs = dataframe.close.rolling(window=3, min_periods=1, center=True).aggregate(lambda x: len(x) == 3 and x.iloc[0] > x.iloc[1] and x.iloc[2] > x.iloc[1])
        maximaIdxs = dataframe.close.rolling(window=3, min_periods=1, center=True).aggregate(lambda x: len(x) == 3 and x.iloc[0] < x.iloc[1] and x.iloc[2] < x.iloc[1])
        data["minimaIdxs"] = minimaIdxs
        data["maximaIdxs"] = maximaIdxs
        return pd.DataFrame(index=dataframe.index, data=data)
        
    def consecutive_duplicates_pivot_points(self, dataframe) -> DataFrame:
        """
        Naive Pivots Points:
        https://towardsdatascience.com/programmatic-identification-of-support-resistance-trend-lines-with-python-d797a4a90530
        Formula:
        Caluculate pivot points based on rolling window when the middle candle
        is lower or higher then the others 
        AND considering adjacent candles with same close value by remove them.
        ...
        :param dataframe:
        :return: dataframe
        """
        data = {}
        dataframe = dataframe.close.loc[dataframe.close.shift(-1) != dataframe.close]
        minimaIdxs = dataframe.rolling(window=3, min_periods=1, center=True).aggregate(lambda x: len(x) == 3 and x.iloc[0] > x.iloc[1] and x.iloc[2] > x.iloc[1])
        maximaIdxs = dataframe.rolling(window=3, min_periods=1, center=True).aggregate(lambda x: len(x) == 3 and x.iloc[0] < x.iloc[1] and x.iloc[2] < x.iloc[1])
        data["minimaIdxs"] = minimaIdxs
        data["maximaIdxs"] = maximaIdxs
        return pd.DataFrame(index=dataframe.index, data=data)

    def mom_and_momacc(self, dataframe) -> DataFrame:
        data = {}
        dx = 1
        d_dx = FinDiff(0, dx, 1)
        d2_dx2 = FinDiff(0, dx, 2)
        clarr = np.asarray(dataframe.close)
        mom, momacc = d_dx(clarr), d2_dx2(clarr)
        data["mom"] = mom
        data["momacc"] = momacc
        return pd.DataFrame(index=dataframe.index, data=data)

    def differential_pivot_points(self, dataframe) -> DataFrame:
        data = {}
        data["diff_min"] = dataframe.mom.rolling(window=2, min_periods=1).aggregate(lambda x: len(x)==2 and x.iloc[0]<0 and x.iloc[1]>0)
        data["diff_max"] = dataframe.mom.rolling(window=2, min_periods=1).aggregate(lambda x: len(x)==2 and x.iloc[0]>0 and x.iloc[1]<0)
        return pd.DataFrame(index=dataframe.index, data=data)
        
if __name__ == "__main__":
    print("Program started...")
    dataframe=pd.read_json(r"/freqtrade/user_data/data/binance/BTC_USDT-1d.json")
    print(dataframe)
