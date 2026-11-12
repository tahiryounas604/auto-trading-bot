//+------------------------------------------------------------------+
//|                                  Tytechlabs_SMA_Crossover.mq5    |
//|  Tytechlabs auto-trading-bot v0.1 — SMA crossover EA for MT5       |
//|  Mirrors the Python SMACrossoverStrategy (fast SMA crosses above  |
//|  slow SMA -> buy; crosses below -> close). Long-only.              |
//|                                                                  |
//|  KNOWN LIMIT: this file CANNOT be compiled or tested in the Linux  |
//|  VM used to build this project — MetaTrader 5 / MetaEditor only   |
//|  run on Windows (or Wine). Compile it in MetaEditor before use,   |
//|  test it in the Strategy Tester on a DEMO account first, and      |
//|  never run any EA on a live account without paper testing.        |
//|  Trading can lose money. Past performance means nothing.           |
//+------------------------------------------------------------------+
#property copyright "Tahir Younas — Tytechlabs"
#property link      "https://www.linkedin.com/in/tahiryounas604"
#property version   "0.1.0"
#property strict

#include <Trade\Trade.mqh>
CTrade trade;

//--- Inputs (same defaults as the Python strategy)
input int    InpFastMAPeriod = 10;     // Fast SMA period
input int    InpSlowMAPeriod = 30;     // Slow SMA period
input double InpLotSize      = 0.01;   // Fixed lot size
input int    InpStopLossPts  = 200;    // Stop loss in points (0 = disabled)
input int    InpTakeProfitPts= 400;    // Take profit in points (0 = disabled)
input long   InpMagicNumber  = 20261112; // Magic number for this EA's trades

int    fastHandle = INVALID_HANDLE;
int    slowHandle = INVALID_HANDLE;
double fastBuf[];
double slowBuf[];

//+------------------------------------------------------------------+
//| Expert initialisation                                            |
//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpFastMAPeriod >= InpSlowMAPeriod)
     {
      Print("Fast period must be smaller than slow period.");
      return(INIT_PARAMETERS_INCORRECT);
     }
   fastHandle = iMA(_Symbol, PERIOD_CURRENT, InpFastMAPeriod, 0, MODE_SMA, PRICE_CLOSE);
   slowHandle = iMA(_Symbol, PERIOD_CURRENT, InpSlowMAPeriod, 0, MODE_SMA, PRICE_CLOSE);
   if(fastHandle == INVALID_HANDLE || slowHandle == INVALID_HANDLE)
     {
      Print("Failed to create indicator handles.");
      return(INIT_FAILED);
     }
   trade.SetExpertMagicNumber(InpMagicNumber);
   ArraySetAsSeries(fastBuf, true);
   ArraySetAsSeries(slowBuf, true);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Expert deinitialisation                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(fastHandle != INVALID_HANDLE) IndicatorRelease(fastHandle);
   if(slowHandle != INVALID_HANDLE) IndicatorRelease(slowHandle);
  }

//+------------------------------------------------------------------+
//| True when this EA already holds an open position on this symbol   |
//+------------------------------------------------------------------+
bool HasOpenPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber
         && PositionGetString(POSITION_SYMBOL) == _Symbol)
         return true;
     }
   return false;
  }

//+------------------------------------------------------------------+
//| Tick handler: one signal evaluation per tick; trades only on a    |
//| confirmed crossover of the two most recent closed values.        |
//+------------------------------------------------------------------+
void OnTick()
  {
   if(CopyBuffer(fastHandle, 0, 1, 2, fastBuf) < 2) return;
   if(CopyBuffer(slowHandle, 0, 1, 2, slowBuf) < 2) return;

   double fastPrev = fastBuf[1], fastNow = fastBuf[0];
   double slowPrev = slowBuf[1], slowNow = slowBuf[0];

   bool crossUp   = (fastPrev <= slowPrev && fastNow >  slowNow);
   bool crossDown = (fastPrev >= slowPrev && fastNow <  slowNow);
   bool inPosition = HasOpenPosition();

   if(crossUp && !inPosition)
     {
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
      double sl = (InpStopLossPts   > 0) ? ask - InpStopLossPts   * point : 0;
      double tp = (InpTakeProfitPts > 0) ? ask + InpTakeProfitPts * point : 0;
      if(!trade.Buy(InpLotSize, _Symbol, ask, sl, tp, "Tytechlabs SMA crossover"))
         Print("Buy failed: ", trade.ResultRetcodeDescription());
     }
   else if(crossDown && inPosition)
     {
      if(!trade.PositionClose(_Symbol))
         Print("Close failed: ", trade.ResultRetcodeDescription());
     }
  }
//+------------------------------------------------------------------+
