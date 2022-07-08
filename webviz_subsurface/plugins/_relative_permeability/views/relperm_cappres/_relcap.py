from typing import List, Tuple, Optional, Union
from pathlib import Path

from dash import callback, Input, Output, State
import pandas as pd
import plotly.colors
from webviz_config.webviz_plugin_subclasses import ViewABC

from ..._plugin_ids import PlugInIDs
from ...view_elements import Graph

class RelpermCappres(ViewABC):
    '''Add comment descibring the plugin'''
    class IDs:
        '''Different curves to be shown in the view'''
        #pylint: disable=too-few-public-methods
        # en ID pr view element; ett eller to view element?
        # tror jeg går for to view elements
        RELATIVE_PERMEABILIY = "reative-permeability"
        CAPILAR_PRESSURE = "capilar-pressure"

        # don't think I need these
        '''KRW = "KRW"
        KROW = "KROW"
        POW = "POW"

        class Saturations:
            SW = "SW"
            SO = "SO"
            SG = "SG"
            SL = "SL"
        class RelpermFamilies: # the possible keywords in the data files needed in list
            SWOF = "SWOF"
            SGOF = "SGOF"
            SLGOF = "SLGOF"
            SWFN = "SWFN"
            SGFN = "SGFN"
            SOF3 = "SOF3"'''

    # maybe need to add a create csv file in the main class to create one csv file
        
    SATURATIONS = ["SW", "SO", "SG", "SL"]
    RELPERM_FAMILIES = ["SWOF", "SGOF", "SLGOF","SWFN", "SGFN", "SOF3"]
    ENSAMBLES = ["iter-0","iter-3"]
    GRAPHS = ["KRW","KRG","KROG","KROW","PCOW","PCOG"]

    # må ha en utvidet csv fil som har realization og ensamble kolonne
    valid_columns = (["ENSEMBLE", "REAL", "KEYWORD", "SATNUM"] + SATURATIONS + GRAPHS)
    
    
    # stat types; should include al so it works on all data (copied)
    SATURATIONS = ["SW", "SO", "SG", "SL"] # only sw and sg are used so far
    RELPERM_FAMILIES = {
        1: ["SWOF", "SGOF", "SLGOF"], # only SWOF and SGOF re use in test data
        2: ["SWFN", "SGFN", "SOF3"],
    }
    SCAL_COLORMAP = {
        "Missing": "#ffff00",  # using yellow if the curve could not be found
        "KRW": "#0000aa",
        "KRG": "#ff0000",
        "KROG": "#00aa00",
        "KROW": "#00aa00",
        "PCOW": "#555555",  # Reserving #000000 for reference envelope (scal rec)
        "PCOG": "#555555",
    }


    def __init__(self,ensambles: List, relperm_df: pd.DataFrame, scalfile: Path = None,sheet_name: Optional[Union[str, int, list]] = None) -> None:
        # scalfile: Path = None; sets the scal file to be used, if any
        # sheet_name: Optional[Union[str, int, list]] = None which shet to use for the scalfile if it is xlsx formate
        super().__init__("Relatve permeability")

        ''' Data funksjonaliteter

            Dataen er fordelt mellom de som er saturated in w og g (guess water and gass)
            -> Sat ax Sw: kan velge mellom KRW, KROW og POW (tre grupper)
            -> Sat ax Sg: kan velge mellom KRG, KROG og POG
            Alle disse har felles instilliner

            Gruppene er 
            -> KRW: Relative permeability to water
            -> KRG: Rlative permeability to gas 
            -> KROW: Relative permeability of oil in prescence of water
            -> KROG: Relative permeability of oil in prescence of gas afo liwuid saturation
            -> POW/G: Pressure of Water/Gas

            Colr by: velger hvordan man skal fordele dataen innad i de tre gruppene -> ensamble, curve og satnum
            -> Ensamble: velger hvilke og hvor mange iter du skal ha med og velger en satnum. plotter for hver iter
            -> Curve: velger en iter og en satnum, plotter for hver gruppe/kurve
            -> Satnum: velger en iter og en eler flere satnum, plotte for hver satnum
            Men alle har alltid mulighet til velge hvilke(n) gruppe(r) man ønsker å inludere

            De tre ulike gruppene er hver sin graph i viewen; 
            KRx og KROx er plottet sammen mot samme y akse, alle har samme y akse
            -> KROx: oppe fra venstre og ned til høyre
            -> KRx: nede fra venstre og opp til høyre
            -> POx: 
        '''
        ''' Data i fil
            Filene er sortert etter realization; 
            each realization has iter-0 and iter-3
            share -> results -> relperm.csv
            velger realization (99 ulike) og iter (2 uliker pr realization) -> totalt 198 filer

            I hver fil er dataen grupert nedover ettter satnum (og keyword?)
            Så er det listet data først for SW og å for SG or alle satnums

            X-aksen til plottene er definer ut ifra SG og SW som går fra 0 til 1
        '''
        
        # extracte the data for the different graphs from the data source relperm_df
        self.relperm_df = relperm_df # sets the data frame 

        # er det egt flere som kan kunne plottes, men siden det kuner tatt ensyn til sg og sw foreløpig er det bare disse?
        # skal vi inludere for utvidelse eller bare markere hvor det kan legges inn?

        # df for SW og SG
        self.df_SW = self.relperm_df[relperm_df["KEYWORD"] == "SGOF"]
        self.df_SG = self.relperm_df[relperm_df["KEYWORD"] == "SWOF"]


        self.satnum1 = self.relperm_df[self.relperm_df["SATNUM"] == 1] # dette er velidg ueffektivt, er 12 satnum


        # creating the columns and row to define the setup of the view
        column = self.add_column()

        first_row = column.make_row()
        first_row.add_view_element(Graph(),RelpermCappres.IDs.RELATIVE_PERMEABILIY) 
        # change something in Graph() ot be able to get them in the same plot, or add them as on view element?
        # need the height of the Graph() to vary wether we are suppoed to show to graphs or not

        second_row = column.make_row()
        second_row.add_view_element(Graph(),RelpermCappres.IDs.CAPILAR_PRESSURE)

    # define the callbacks of the view
    def set_callbacks(self) -> None:
        # callback for the graphs
        @callback( 
            Output(self.get_unique_id(Graph(),"figure")), # need to be changed
            Input(self.uuid("color_by"), "value"),
            Input(self.uuid("visualization"), "value"),
            Input(self.uuid("ensemble"), "value"),
            Input(self.uuid("curve"), "value"),
            Input(self.uuid("satnum"), "value"),
            Input(self.uuid("sataxis"), "value"),
            Input(self.uuid("linlog"), "value"),
            Input(self.uuid("scal"), "value"),
        )
        def _update_graph(color_by, visualization, ensembles, curves, satnums, sataxis, linlog, scal) -> dict:
            colors = plotly.colors.DEFAULT_PLOTLY_COLORS


        # callback function for the ensamble selector
        @callback( 
            Output(self.uuid("ensemble"), "multi"),
            Output(self.uuid("ensemble"), "value"),
            Input(self.uuid("color_by"), "value"),
            State(self.uuid("stored_ensemble"), "data") #need to fin out how this works
        )
        def _set_ensamble_selector(color_by, stored_ensemble):
            """If ensemble is selected as color by, set the ensemble
            selector to allow multiple selections, else use stored_ensemble
            """

        # callback function for the curve selector
        @callback(

        )
        def _set_curve_selector()