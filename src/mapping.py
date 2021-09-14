import re as regex
import pandas as pd
from owlready2 import *
from quantulum3 import parser
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import os

# variables
dont_parse_specs = ['name', 'Name', 'NAME', 'description', 'Description', 'DESCRIPTION']
cc_sim_thr = 91
pp_sim_thr = 96
cc_output_columns = ['RequestID',
                     'MatchPosition',
                     'TypeofMatch',
                     'Source',
                     'ProductCategory',
                     'ProductClass',
                     'ClassID',
                     'HC',
                     'Score',
                     'Scorer',
                     'UserValidation']
pp_output_columns = ['RequestID',
                     'MatchPosition',
                     'TypeofMatch',
                     'Source',
                     'ProductCategory',
                     'ProductClass',
                     'SpecificationName',
                     'SpecificationUnit',
                     'Example',
                     'MatchedPropertyName',
                     'MatchedPropertyID',
                     'MatchedPropertyType',
                     'MatchedPropertyUnit',
                     'Description',
                     'Ontology',
                     'Score',
                     'Scorer',
                     'UserValidation']
pp_axis = ['PropertyName',
           'UnitName',
           'UnitSymbol',
           'AlternativeName',
           'Description',
           'PropertyType',
           'PropertyID',
           'Domain',
           'HC',
           'ONTOLOGY']
cc_axis = ['ClassName', 'AlternativeName', 'HC', 'ClassID']
items_json_file = 'Data/items.jl'
world_file = 'PCS/eclass11.sqlite3'
mbse_file = 'PCS/mbse-information-model.owl'
cc_output_file = 'Data/class_mapping_result.csv'
pp_output_file = 'Data/property_mapping_result.csv'
units_output_file = 'Data/units_result.jl'
gr_purl = "http://purl.org/goodrelations/v1#"
eclass_purl = 'http://www.intelligent-match.de/eco11/'


def classes_iter(onto):
    for i in onto.classes():
        label = i.label if i.label else None
        HC = i.hierarchyCode if i.hierarchyCode else None
        label2 = i.altLabel if i.altLabel else []
        ID = i.name
        if label and HC:
            for i2, l in enumerate(label):
                label[i2] = regex.sub(" \(Taxonomy.*?\)", "", l)
            try:
                for i2, l in enumerate(label2):
                    label2[i2] = regex.sub(" \(Taxonomy.*?\)", "", l)
            except:
                pass
            yield (label, label2, HC, ID)


def properties_iter(onto):
    for i in onto.properties():
        label = i.label if i.label else None
        unit_name = i.UnitOfMeasurementName if i.UnitOfMeasurementName else None
        unit_symbol = i.UnitOfMeasurementSymbol if i.UnitOfMeasurementSymbol else None
        description = ' '.join(i.comment) if i.comment else None
        label2 = i.altLabel if i.altLabel else []
        if owl.DatatypeProperty in i.is_a:
            pType = owl.DatatypeProperty
        elif owl.ObjectProperty in i.is_a:
            pType = owl.ObjectProperty
        else:
            pType = None
        pID = i.name
        try:
            domain = i.domain[0].Classes if i.domain else None
        except:
            domain = i.domain[0]
        if label:
            try:
                for c in domain:
                    tax_class = [c2 for c2 in c.is_a if '-tax' in c2.name]
                    HC = tax_class[0].hierarchyCode if tax_class else None
                    yield (label, unit_name, unit_symbol, label2, description, pType, pID, c, HC, 'ECLASS')
            except:
                tax_class = [c2 for c2 in domain.is_a if '-tax' in c2.name]
                HC = tax_class[0].hierarchyCode if tax_class else None
                yield (label, unit_name, unit_symbol, label2, description, pType, pID, domain, HC, 'ECLASS')


def namespace_properties_iter(onto, iri_fragment):
    d = {'goodrelations': 'GR', 'schema.org': 'SCHEMA'}
    for i in onto.search(iri='*' + iri_fragment + '*'):
        label = i.label if i.label else None
        label2 = i.altLabel if i.altLabel else []
        description = ' '.join(i.comment) if i.comment else None
        if owl.DatatypeProperty in i.is_a:
            pType = owl.DatatypeProperty
        elif owl.ObjectProperty in i.is_a:
            pType = owl.ObjectProperty
        else:
            pType = None
        pID = i.name
        if label and pType:
            for i2, l in enumerate(label):
                label[i2] = regex.sub(" \(.*?\)", "", l)
            try:
                for i2, l in enumerate(label2):
                    label2[i2] = regex.sub(" \(.*?\)", "", l)
            except:
                pass
            yield (label, None, None, label2, description, pType, pID, None, None, d.get(iri_fragment))


def get_units(df, col_list):
    for c in col_list:
        for i, properties in enumerate(df[c]):
            for specification in properties.items():
                original_value = specification[1]
                value = None
                unit = None
                unit_entity = None
                name = specification[0]
                quants = parser.parse(str(original_value)) if name not in dont_parse_specs else []
                # length measures go separately
                if "Length" not in set(q.unit.entity.uri for q in quants):
                    quants = parser.parse(regex.sub("[\(\[].*?[\)\]]", "", str(original_value).replace(" ", ""))) if \
                        name not in dont_parse_specs else []
                if len(quants) > 1:
                    unit_entities = set(q.unit.entity.uri for q in quants if q.unit.name != 'dimensionless')
                    units = set(q.unit.name for q in quants if q.unit.name != 'dimensionless')
                    if len(units) == 1:
                        unit_entity = unit_entities.pop()
                        value = [q.value for q in quants] if unit_entity else None
                        unit = units.pop() if unit_entity else None
                elif quants and quants[0].unit.name != 'dimensionless':
                    unit_entity = quants[0].unit.entity.uri
                    value = quants[0].value if unit_entity else None
                    unit = quants[0].unit.name if unit_entity else None
                df.loc[i, c][name] = {'value': value, 'unit': unit, 'original_value': original_value,
                                      'entity': unit_entity}


def group_properties(df):
    """
    improve it? change to iterrows to pass structuredData and properties arguments?
    """
    pp_set = set()
    pp_set_2 = set()
    for row in df.itertuples():
        for k in row.StructuredData.items():
            t = (row.Category, row.Source, k[0], k[1]['unit'])
            t2 = (row.Category, row.Source, k[0], k[1]['unit'], k[1]['original_value'], k[1]['entity'])
            if t not in pp_set:
                pp_set.add(t)
                pp_set_2.add(t2)
        for k in row.Properties.items():
            t = (row.Category, row.Source, k[0], k[1]['unit'])
            t2 = (row.Category, row.Source, k[0], k[1]['unit'], k[1]['original_value'], k[1]['entity'])
            if t not in pp_set:
                pp_set.add(t)
                pp_set_2.add(t2)
    df_grouped = pd.DataFrame(pp_set_2)
    df_grouped = df_grouped.set_axis(["ProductCategory", "Source", "SpecificationName",
                                      "SpecificationUnit", "Example", "Entity"], axis='columns')

    # exclude properties with more than 2 different entities
    df_exclude = df_grouped.groupby(['ProductCategory', 'Source', 'SpecificationName'])['Entity'].apply(
        set).reset_index()
    df_exclude['NEntities'] = df_exclude.apply(lambda row: len([x for x in row['Entity'] if x is not None]), axis=1)
    df_exclude = df_exclude.loc[df_exclude['NEntities'] > 1][['ProductCategory', 'Source', 'SpecificationName']]
    df_grouped = pd.merge(df_grouped, df_exclude, how='outer', indicator=True)
    condition = df_grouped['_merge'] == 'both'
    df_grouped_1 = df_grouped.loc[~condition].reset_index(drop=True)
    df_grouped_2 = df_grouped.loc[condition].groupby(
        ['ProductCategory', 'Source', 'SpecificationName']).first().reset_index()
    df_grouped_2['SpecificationUnit'] = None
    df_output = df_grouped_1.append(df_grouped_2, ignore_index=True).drop(['Entity', '_merge'], axis='columns')

    return df_output


def validate_result(stage, file_path, df_units_grouped=None):
    if stage == 'class':
        input('check class mapping result in file below and hit enter \n' + os.getcwd() + "\\" + file_path)
        df_user_validated = pd.read_csv(file_path, delimiter=";")
        df_user_validated = df_user_validated.loc[~pd.isna(df_user_validated['UserValidation'])].drop_duplicates(
            subset='RequestID')
        right = df_user_validated[['Source', 'ProductCategory', 'ClassID', 'HC']]
        df_cc_result = pd.merge(df_units_grouped, right, on=['Source', 'ProductCategory'])
        return df_cc_result

    elif stage == 'properties':
        input('check property mapping result in file below and hit enter \n' + os.getcwd() + "\\" + file_path)
        return True

    return None


def map_classes(onto, df_units_grouped):
    df_cc = pd.DataFrame(classes_iter(onto))
    df_cc = df_cc.set_axis(cc_axis, axis='columns')
    df_cc = df_cc.explode('HC')
    df_cc['HC'] = pd.to_numeric(df_cc['HC'])
    df_cc['Labels'] = df_cc['ClassName'] + df_cc['AlternativeName']
    df_cc_lab = df_cc['ClassName'] + df_cc['AlternativeName']
    df_cc_lab = df_cc_lab.explode().drop_duplicates()

    df_cc_units = df_units_grouped[['ProductCategory', 'Source']].drop_duplicates()
    df_cc_units = df_cc_units.reset_index(drop=True)

    df_cc_result = pd.DataFrame(columns=cc_output_columns)

    total_cc = len(df_cc_units)
    for element in df_cc_units.itertuples():
        print('\r', 'processing category %s (%s/%s)' % (element.ProductCategory, element.Index + 1, total_cc), end='')
        results = match_class(df_cc, df_cc_lab, cc_sim_thr, element.ProductCategory, element.Source, element.Index + 1,
                              fuzz.WRatio)
        for r in results:
            df_cc_result = df_cc_result.append(r, ignore_index=True)

    return df_cc_result


def match_class(df, df_aux, sim_thr, prod_category, source, RequestID, scorer):
    """
    returns a list of dictionaries with the following style:
    {"RequestID": "..."
    "MatchPosition": "...",
    "TypeofMatch": "...",
    "Source": "...",
    "ProductCategory":"...",
    "ProductClass":"...",
    "ClassID": "..."
    "HC": "..."
    "Score": "...",
    "Scorer":"...")}
    """
    if prod_category:
        cc_candidates = process.extractBests(prod_category, df_aux, score_cutoff=sim_thr, limit=10, scorer=scorer)
    else:
        cc_candidates = None
    if cc_candidates:
        if len(cc_candidates) > 1 and cc_candidates[0][1] == cc_candidates[1][1]:
            # multiple matches
            return [{"RequestID": RequestID,
                     "MatchPosition": pos + 1,
                     "TypeofMatch": "multiple matches",
                     "Source": source,
                     "ProductCategory": prod_category,
                     "ProductClass": candidate[0],
                     "ClassID": df.loc[candidate[2], 'ClassID'],
                     "HC": df.loc[candidate[2], 'HC'],
                     "Score": candidate[1],
                     "Scorer": "WRatio"} for pos, candidate in enumerate(cc_candidates)]
        else:
            # unique match
            return [{"RequestID": RequestID,
                     "MatchPosition": 1,
                     "TypeofMatch": "unique match",
                     "Source": source,
                     "ProductCategory": prod_category,
                     "ProductClass": cc_candidates[0][0],
                     "ClassID": df.loc[cc_candidates[0][2], 'ClassID'],
                     "HC": df.loc[cc_candidates[0][2], 'HC'],
                     "Score": cc_candidates[0][1],
                     "Scorer": "WRatio"}]
    else:
        # no match
        return [{"RequestID": RequestID,
                 "MatchPosition": 1,
                 "TypeofMatch": "category not found",
                 "Source": source,
                 "ProductCategory": prod_category,
                 "ProductClass": None,
                 "ClassID": None,
                 "HC": None,
                 "Score": None,
                 "Scorer": "WRatio"}]


def map_properties(onto, df_cc_result):
    #print('mapping properties!!')
    df_gr = pd.DataFrame(namespace_properties_iter(onto, 'goodrelations'))
    df_gr = df_gr.set_axis(pp_axis, axis='columns')
    df_schema = pd.DataFrame(namespace_properties_iter(onto, 'schema.org'))
    df_schema = df_schema.set_axis(pp_axis, axis='columns')

    df_pp = pd.DataFrame(properties_iter(onto))
    df_pp = df_pp.set_axis(pp_axis, axis='columns')
    df_pp = df_pp.explode('HC')
    df_pp['HC'] = pd.to_numeric(df_pp['HC'])
    df_pp = df_pp.append(df_gr, ignore_index=True)
    df_pp = df_pp.append(df_schema, ignore_index=True)
    df_pp['Labels'] = df_pp['PropertyName'] + df_pp['AlternativeName']

    units = df_pp.loc[df_pp['UnitName'].astype(bool), ['UnitName']].explode('UnitName')['UnitName'].unique()
    df_units = df_pp.drop_duplicates(subset='PropertyID')[['PropertyID', 'UnitName', 'PropertyType']]

    df_pp_result = pd.DataFrame(columns=pp_output_columns)
    total_pp = len(df_cc_result.index)

    for element in df_cc_result.itertuples():
        print('processing property (name: %s, unit: %s) %s/%s' % (element.SpecificationName, element.SpecificationUnit,
                                                         element.Index + 1, total_pp), end='\r')
        results = match_property(df_pp, pp_sim_thr, element.HC, element.SpecificationName,
                                 element.SpecificationUnit, element.ProductCategory,
                                 element.ClassID, element.Source, element.Example, element.Index + 1,
                                 fuzz.WRatio, units, df_units)
        for r in results:
            df_pp_result = df_pp_result.append(r, ignore_index=True)

    return df_pp_result


def match_property(df, sim_thr, HC, spec_name, spec_unit, prod_category, prod_class, source, example, RequestID, scorer,
                   units, df_units):
    """
    returns a list of dictionaries with the following style:

    {"RequestID": "..."
    "MatchPosition": "...",
    "TypeofMatch": "...",
    "Source": "...",
    "ProductCategory":"...",
    "ProductClass":"...",
    "SpecificationName": "...",
    "SpecificationUnit": "...",
    "MatchedPropertyName" = "...",
    "MatchedPropertyID": "...",
    "MatchedPropertyType": "...",
    "MatchedPropertyUnit": "...",
    "Ontology": "...",
    "Score": "...",
    "Scorer":"...")}

    r = 1 means unique match found
    r = 2 means multiple matches found
    r = 3 means no match found
    """

    r = None

    # apply unit mask if there is a unit
    unit_mask = True
    if spec_unit and units.any():
        u_candidate = process.extractBests(spec_unit, units, score_cutoff=99, limit=1, scorer=fuzz.ratio)
        if u_candidate:
            um = df_units.apply(lambda row: u_candidate[0][0] in row['UnitName'] if row['UnitName'] and
                                                row['PropertyType'] == owl.ObjectProperty else False, axis=1)
            unit_mask = pd.merge(df, df_units.loc[um], on='PropertyID', how='left', indicator=True)['_merge'] == 'both'

    # first try to match against GR and SCHEMA properties
    pp_set = df.loc[(df['ONTOLOGY'] != 'ECLASS') & unit_mask, ['Labels', 'PropertyID']].drop_duplicates(subset=
                                                                                                        ['PropertyID'])
    if not pp_set.empty:
        pp_set = pp_set.explode('Labels')
        pp_candidates = process.extractBests(spec_name, pp_set['Labels'], score_cutoff=sim_thr, limit=10,
                                             scorer=scorer)
        if pp_candidates:
            if len(pp_candidates) > 2 and pp_candidates[0][1] == pp_candidates[1][1]:
                r = 2
            else:
                r = 1

    # for later, only consider Eclass properties
    ECLASS_mask = df['ONTOLOGY'] == 'ECLASS'

    # start iterations to find properties
    i = 0
    i_max = 3
    while not r:
        # in the last iteration consider all properties even without domains
        if i > i_max:
            pp_set = df.loc[ECLASS_mask & unit_mask, ['Labels', 'PropertyID']].drop_duplicates(subset=['PropertyID'])
        else:
            mask1 = df['HC'] >= (HC - (HC % 10 ** (i * 2)))
            mask2 = df['HC'] <= (HC - (HC % 10 ** (i * 2)) + 10 ** (i * 2))
            pp_set = df.loc[ECLASS_mask & mask1 & mask2 & unit_mask, ['Labels',
                                                                  'PropertyID']].drop_duplicates(subset=['PropertyID'])
        if not pp_set.empty:
            pp_set = pp_set.explode('Labels')
            pp_candidates = process.extractBests(spec_name, pp_set['Labels'],
                                                 score_cutoff=sim_thr, limit=10, scorer=scorer)
        else:
            pp_candidates = None
        if pp_candidates:
            if len(pp_candidates) > 2 and pp_candidates[0][1] == pp_candidates[1][1]:
                r = 2
            else:
                r = 1

        # last iteration
        if i > i_max:
            # try the match without unit, in case it was not well read by quantulum3
            if spec_unit: #alternative: i = -1, unit_mask = True (then the loop restarts without unit_mask)
                pp_set = df[['Labels', 'PropertyID']].drop_duplicates(subset=['PropertyID'])
                pp_set = pp_set.explode('Labels')
                pp_candidates = process.extractBests(spec_name, pp_set['Labels'],
                                                     score_cutoff=sim_thr, limit=10,
                                                     scorer=scorer)
                if pp_candidates:
                    if len(pp_candidates) > 2 and pp_candidates[0][1] == pp_candidates[1][1]:
                        r = 2
                    else:
                        r = 1
            if not r: r = 3
        i += 1
    if r == 1:
        # unique match
        return [{"RequestID": RequestID,
                 "MatchPosition": 1,
                 "TypeofMatch": "unique match",
                 "Source": source,
                 "ProductCategory": prod_category,
                 "ProductClass": prod_class,
                 "SpecificationName": spec_name,
                 "SpecificationUnit": spec_unit,
                 "Example": example,
                 "MatchedPropertyName": pp_candidates[0][0],
                 "MatchedPropertyID": df.loc[pp_candidates[0][2], 'PropertyID'],
                 "MatchedPropertyType": df.loc[pp_candidates[0][2], 'PropertyType'],
                 "MatchedPropertyUnit": df.loc[pp_candidates[0][2], 'UnitName'],
                 "Description": df.loc[pp_candidates[0][2], 'Description'],
                 "Ontology": df.loc[pp_candidates[0][2], 'ONTOLOGY'],
                 "Score": pp_candidates[0][1],
                 "Scorer": "WRatio"}]
    elif r == 2:
        # multiple match
        return [{"RequestID": RequestID,
                 "MatchPosition": pos + 1,
                 "TypeofMatch": "multiple matches",
                 "Source": source,
                 "ProductCategory": prod_category,
                 "ProductClass": prod_class,
                 "SpecificationName": spec_name,
                 "SpecificationUnit": spec_unit,
                 "Example": example,
                 "MatchedPropertyName": candidate[0],
                 "MatchedPropertyID": df.loc[candidate[2], 'PropertyID'],
                 "MatchedPropertyType": df.loc[candidate[2], 'PropertyType'],
                 "MatchedPropertyUnit": df.loc[candidate[2], 'UnitName'],
                 "Description": df.loc[candidate[2], 'Description'],
                 "Ontology": df.loc[candidate[2], 'ONTOLOGY'],
                 "Score": candidate[1],
                 "Scorer": "WRatio"} for pos, candidate in enumerate(pp_candidates)]
    elif r == 3:
        # not match
        return [{"RequestID": RequestID,
                 "MatchPosition": 1,
                 "TypeofMatch": "property not found",
                 "Source": source,
                 "ProductCategory": prod_category,
                 "ProductClass": prod_class,
                 "SpecificationName": spec_name,
                 "SpecificationUnit": spec_unit,
                 "Example": example,
                 "MatchedPropertyName": None,
                 "MatchedPropertyID": None,
                 "MatchedPropertyType": None,
                 "MatchedPropertyUnit": None,
                 "Description": None,
                 "Ontology": None,
                 "Score": None,
                 "Scorer": "WRatio"}]


def mapping(onto):

    print('Reading scraped items...')
    df_units = pd.read_json(items_json_file, lines=True)
    get_units(df_units, ['StructuredData', 'Properties'])
    df_units_grouped = group_properties(df_units)
    df_units.to_json(units_output_file)

    print('Mapping classes...')
    df_cc_result = map_classes(onto, df_units_grouped)
    df_cc_result.to_csv(cc_output_file, sep=';', index=False)
    df_cc_result = validate_result('class', cc_output_file, df_units_grouped)

    print('Mapping properties...')
    df_pp_result = map_properties(onto, df_cc_result)
    df_pp_result.to_csv(pp_output_file, sep=';', index=False)

    status = validate_result('properties', pp_output_file)

    if status:
        print('mapping process executed correctly!')


if __name__ == '__main__':
    print('Loading Database...')
    MyWorld = World(filename=world_file)
    print('Loading Ontology...')
    onto = MyWorld.get_ontology(eclass_purl).load()
    mapping(onto)
