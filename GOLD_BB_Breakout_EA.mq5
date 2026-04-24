//+------------------------------------------------------------------+
//|                                        GOLD_BB_Breakout_EA.mq5 |
//|                                      Copyright 2026, Antigravity |
//+------------------------------------------------------------------+
#property copyright "Antigravity"
#property link      ""
#property version   "1.00"

#include <Trade\Trade.mqh>

//--- Input parameters
input string   Group1 = "--- Strategy Settings ---";
input int      InpBBPeriod       = 20;       // Bollinger Bands Period
input double   InpBBDev          = 2.0;      // Bollinger Bands Deviation
input double   InpRRRatio        = 5.0;      // Risk/Reward Ratio (e.g. 5.0 for 1:5)
input double   InpMinBreakPct    = 0.0;      // Minimum Breakout % (e.g. 0.2)

input string   Group2 = "--- Trade Management ---";
input double   InpLotSize        = 0.1;      // Lot Size
input int      InpExpirationBars = 120;      // Pending Order Expiration (Bars)
input int      InpATRPeriod      = 14;       // ATR Period (for min risk)
input ulong    InpMagicNumber    = 123456;   // Magic Number

CTrade         trade;
int            bb_handle;
int            atr_handle;

//--- State variables for confirmation
bool           wait_confirmation = false;
int            breakout_type     = 0;        // 1 for BUY, -1 for SELL
double         entry_price       = 0.0;
datetime       breakout_time     = 0;

datetime       last_bar_time     = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   // Initialize indicators
   bb_handle = iBands(_Symbol, _Period, InpBBPeriod, 0, InpBBDev, PRICE_CLOSE);
   atr_handle = iATR(_Symbol, _Period, InpATRPeriod);
   
   if(bb_handle == INVALID_HANDLE || atr_handle == INVALID_HANDLE)
     {
      Print("Error initializing indicators");
      return(INIT_FAILED);
     }
     
   trade.SetExpertMagicNumber(InpMagicNumber);
   
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   IndicatorRelease(bb_handle);
   IndicatorRelease(atr_handle);
  }

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
  {
   // Only run once per bar (when a new bar opens)
   datetime current_bar_time = iTime(_Symbol, _Period, 0);
   if(current_bar_time == last_bar_time) return; 
   last_bar_time = current_bar_time;
   
   double bb_upper[1], bb_lower[1], atr[1];
   double high[1], low[1];
   
   // Copy data from shift = 1 (the bar that just closed)
   if(CopyBuffer(bb_handle, 1, 1, 1, bb_upper) <= 0) return;
   if(CopyBuffer(bb_handle, 2, 1, 1, bb_lower) <= 0) return;
   if(CopyBuffer(atr_handle, 0, 1, 1, atr) <= 0) return;
   if(CopyHigh(_Symbol, _Period, 1, 1, high) <= 0) return;
   if(CopyLow(_Symbol, _Period, 1, 1, low) <= 0) return;
   
   double bb_up = bb_upper[0];
   double bb_dn = bb_lower[0];
   double atr_val = atr[0];
   double h = high[0];
   double l = low[0];
   
   //---------------------------------------------------------
   // 1. Check Confirmation (Wait for nến [1] to close)
   //---------------------------------------------------------
   if(wait_confirmation)
     {
      double sl_price = 0.0;
      double risk = 0.0;
      
      long stop_level = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
      double min_stop_dist = stop_level * _Point;
      double min_risk = MathMax(atr_val * 0.05, min_stop_dist); // Enforce minimum risk of 0.05 ATR or broker stop level
      
      if(breakout_type == 1) // Setup BUY
        {
         sl_price = l; // SL is the low of the confirmation candle
         risk = entry_price - sl_price;
         
         // If confirmation candle didn't pull back enough, enforce min risk
         if(risk < min_risk) { 
            risk = min_risk; 
            sl_price = entry_price - risk; 
         }
         
         double tp_price = entry_price + risk * InpRRRatio;
         
         // Normalize prices
         sl_price = NormalizeDouble(sl_price, _Digits);
         tp_price = NormalizeDouble(tp_price, _Digits);
         double e_price = NormalizeDouble(entry_price, _Digits);
         
         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         bool res = false;
         
         if(e_price < ask)
            res = trade.BuyLimit(InpLotSize, e_price, _Symbol, sl_price, tp_price, ORDER_TIME_GTC);
         else
            res = trade.BuyStop(InpLotSize, e_price, _Symbol, sl_price, tp_price, ORDER_TIME_GTC);
            
         if(!res) Print("BUY Order Error: ", trade.ResultRetcode(), " - ", trade.ResultRetcodeDescription());
        }
      else if(breakout_type == -1) // Setup SELL
        {
         sl_price = h; // SL is the high of the confirmation candle
         risk = sl_price - entry_price;
         
         if(risk < min_risk) { 
            risk = min_risk; 
            sl_price = entry_price + risk; 
         }
         
         double tp_price = entry_price - risk * InpRRRatio;
         
         // Normalize prices
         sl_price = NormalizeDouble(sl_price, _Digits);
         tp_price = NormalizeDouble(tp_price, _Digits);
         double e_price = NormalizeDouble(entry_price, _Digits);
         
         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         bool res = false;
         
         if(e_price > bid)
            res = trade.SellLimit(InpLotSize, e_price, _Symbol, sl_price, tp_price, ORDER_TIME_GTC);
         else
            res = trade.SellStop(InpLotSize, e_price, _Symbol, sl_price, tp_price, ORDER_TIME_GTC);
            
         if(!res) Print("SELL Order Error: ", trade.ResultRetcode(), " - ", trade.ResultRetcodeDescription());
        }
      
      // Reset confirmation state
      wait_confirmation = false;
      breakout_type = 0;
     }
   
   //---------------------------------------------------------
   // 2. Scan for NEW Breakout (on the bar that just closed)
   //---------------------------------------------------------
   double up_pct = (h - bb_up) / bb_up * 100.0;
   double dn_pct = (bb_dn - l) / bb_dn * 100.0;
   
   if(l < bb_dn && dn_pct >= InpMinBreakPct)
     {
      // Found a BUY breakout
      wait_confirmation = true;
      breakout_type = 1;
      entry_price = l; // Entry is the Low of the breakout candle
      breakout_time = iTime(_Symbol, _Period, 1);
     }
   else if(h > bb_up && up_pct >= InpMinBreakPct)
     {
      // Found a SELL breakout
      wait_confirmation = true;
      breakout_type = -1;
      entry_price = h; // Entry is the High of the breakout candle
      breakout_time = iTime(_Symbol, _Period, 1);
     }
  }
//+------------------------------------------------------------------+
