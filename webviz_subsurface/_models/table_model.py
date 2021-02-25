from typing import List
import pandas as pd


class EnsembleTableModel
    def column_names() -> List[str]: ...
    def has_column(str) -> boolean: ...
    def has_columns(List[str]) -> boolean: ...

    def realizations() -> List[int]: ...

    def get_column_values(column_name, realizations: Optional[Sequence[int]]) ->
    def get_realizations_based_on_filter(filter_column_name: str, column_values: list) -> Sequence[int]: ...




class EnsembleSetTableModel
    @staticmethod
    def fromEnsembleLayout(ensembles: Dict[str, path], csv_file, selector_columns, filter_columns) -> EnsembleSetTableModel: 
        ensembleset = EnsembleSetTableModel()
        for ens in ensemble
            new_ensemble = EnsembleModel_ensembleLayout()
            ensembleset.add_ensemble(new_ensemble)
        return ensembleset

    @staticmethod
    def fromAggrCsvFile(aggr_csv_file, selector_columns, filter_columns) -> EnsembleSetTableModel: ...
        # Read CSV file
        # Split into ensembles
        # Create EnsembleModel_csvBased for each ensemble
        
        ensembleset = EnsembleSetTableModel()
        return ensembleset

    def ensemble_names(self) -> List[str]: ...
    def ensemble(name) -> EnsembleTable: ...

    # Tja...
    def selector_columns(self) -> List:
    def filter_columns(self) -> List:



class EnsembleModel_ensembleLayout(EnsembleTableModel):
class EnsembleModel_csvBased(EnsembleTableModel):






class Plugin:
    def __init__(self, ensembles, csv_file, aggr_csv_file):

        if (ensembles and fromEnsembleLayout):
            self.enssettablemodel = EnsembleSetTableModel.fromEnsembleLayout(ensembles, csv_file)
        else:
            self.enssettablemodel = EnsembleSetTableModel.fromAggrCsvFile(aggr_csv_file)

    # Long term :-)
    #def __init__(self, ensemble_set_table_model: EnsembleSetTableModele):
    #    self.enssettablemodel = ensemble_set_table_model



    def layout:

        dropdown("available ensembles")
        dropdown("columns available for plotting")
        dropdown("filter on value in some column")
        figure

    def callbacks:
        

        