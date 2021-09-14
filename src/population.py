import pandas as pd
from owlready2 import *

# variables
units_file = 'Data/units_result.jl'
pp_file = 'Data/property_mapping_result.csv'
col_df_units = ['ProductLink',
                'Source',
                'StartTime',
                'EndTime',
                'DownloadTime',
                'Organization',
                'Name',
                'ProductCategory',
                'StructuredData',
                'Properties']
col_df_pp_uv = ['RequestID',
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


# Functions
def update_vocabulary(onto, gr, df_pp_uv):
    for row in df_pp_uv.itertuples():
        p_name = row.MatchedPropertyID.replace(" ", "_")
        with onto:
            if onto[p_name]:
                onto_property = onto[p_name]
            elif 'DatatypeProperty' in row.MatchedPropertyType:
                onto_property = types.new_class(p_name, (DataProperty, gr.datatypeProductOrServiceProperty))
            elif 'ObjectProperty' in row.MatchedPropertyType:
                onto_property = types.new_class(p_name, (ObjectProperty, gr.quantitativeProductOrServiceProperty))

        SpecificationUnit = row.SpecificationUnit if not pd.isna(row.SpecificationUnit) else None

        update_property(onto, gr, onto_property, row.SpecificationName, SpecificationUnit, row.ProductClass)


def update_property(onto, gr, p, specification_name, specification_unit, taxonomic_class):
    target_class = [c for c in onto[taxonomic_class].subclasses() if '-gen' in c.name][0]
    #print(p, target_class)
    # update label or alternative label
    if not p.label:
        p.label.append(specification_name)
    elif specification_name not in p.label:
        if not p.altLabel or specification_name not in p.altLabel:
            p.altLabel.append(specification_name)

    # update unit
    if specification_unit and specification_unit not in p.UnitOfMeasurementName:
        p.UnitOfMeasurementName.append(specification_unit)

    # update domain
    if p.domain:
        if isinstance(p.domain[0], ThingClass):
            if target_class != p.domain[0]:
                p.domain = [Or([p.domain[0], target_class])]
        else:
            try:
                l_cls = p.domain[0].Classes
                if target_class not in l_cls:
                    l_cls.append(target_class)
                    p.domain = [Or(l_cls)]
            except:
                #print('domain could not be updated for %s' % p)
                pass
    else:
        p.domain.append(target_class)

    # update range (only object property quantitativeValueFloat)
    if owl.ObjectProperty in p.is_a:
        if not p.range: p.range = gr.QuantitativeValueFloat


def generate_instances(onto, gr, mbse, schemaorg, skos, df_units_r, df_pp_uv):
    for product in df_units_r.itertuples():
        taxonomic_class = product.ProductClass
        product_link = product.ProductLink
        name = product.Name
        organization_name = product.Organization
        category = product.ProductCategory
        timestamp = product.StartTime
        dics = [product.StructuredData.items(), product.Properties.items()]

        specs = set()
        target_class = [c for c in onto[taxonomic_class].subclasses() if '-gen' in c.name][0]

        someItem = gr.SomeItems(label=[name])
        onto.ECLASSType[someItem] = [target_class]
        gr['category'][someItem] = [category]

        offering = gr.Offering(includes=[someItem])
        mbse.describes[offering] = [someItem]

        organization = None
        for org in onto.search(iri='http://purl.org/goodrelations/v1#businessentity*'):
            if organization_name == org.label[0] or organization_name in org.altLabel:
                organization = org
                break
        if not organization:
            organization = gr.BusinessEntity(label=[organization_name])

        gr['offers'][organization].append(offering)

        ic = mbse.information_concretization(concretizes=[offering],
                                             timestamp=[timestamp],
                                             submitted_by=[mbse.Miguel],
                                             expressed_in=[mbse.HTML],
                                             authored_by=[organization])

        wp = None
        for webpage in onto.search(iri='http://david.org/informationmodel.owl#webpage*'):
            if product_link == webpage.label[0]:
                wp = webpage
                break
        if not wp:
            wp = mbse.Webpage(label=product_link)
        wp.captures.append(ic)

        for d in dics:
            for pair in d:
                # properties where unit was not well read represent a problem here!
                spec_name = pair[0]
                spec_value = pair[1]['value']
                spec_unit = pair[1]['unit']
                spec_value_orig = pair[1]['original_value']

                mask1 = df_pp_uv['SpecificationName'] == spec_name
                mask2 = df_pp_uv['SpecificationUnit'] == spec_unit if spec_unit else pd.isna(
                    df_pp_uv['SpecificationUnit'])
                mapping = df_pp_uv.loc[mask1 & mask2, ['SpecificationName', 'SpecificationUnit',
                                                       'MatchedPropertyID', 'Ontology']].drop_duplicates()

                # if the unit was droped in the mapping phase, read the spec_name without unit
                if mapping.empty:
                    mask2 = pd.isna(df_pp_uv['SpecificationUnit'])
                    mapping = df_pp_uv.loc[mask1 & mask2, ['SpecificationName', 'SpecificationUnit',
                                                           'MatchedPropertyID', 'Ontology']].drop_duplicates()

                mapping = mapping.reset_index(drop=True)

                if len(mapping.index) == 1:
                    p_name = mapping['MatchedPropertyID'][0].replace(" ", "_")
                    p_unit = spec_unit
                    p_value = spec_value
                    p_value_orig = spec_value_orig
                    # print(mapping['Ontology'][0], p_name, p_unit, p_value, p_value_orig)

                    if mapping['Ontology'][0] == 'GR':
                        property_instance_gr(gr, p_name, p_unit, p_value_orig, someItem, offering)

                    elif mapping['Ontology'][0] == 'ECLASS':
                        property_instance(onto, gr, p_name, p_unit, p_value, p_value_orig, someItem)

                    # special case, SKOS are annotation properties
                    elif mapping['Ontology'][0] == 'SKOS':
                        skos[p_name][someItem].append(p_name)

                    # special case, only for availability property
                    elif mapping['Ontology'][0] == 'SCHEMA':
                        property_instance_schema(schemaorg, p_name, p_unit, p_value_orig, someItem, offering)

                    if p_name not in specs:
                        specs.add(spec_name)
                    else:
                        pass
                        # print('property repeated for product ' + product.productLink)
                else:
                    pass
                    # print('not found', pair)


def property_instance(onto, gr, p_name, p_unit, p_value, p_value_orig, someItem):
    # object property
    if ObjectProperty in onto[p_name].is_a:

        if p_value and p_unit:
            if not isinstance(p_value, list):
                qi = gr.QuantitativeValue()
                onto[p_name][someItem].append(qi)
                gr.hasValue[qi].append(p_value)
                gr.hasUnitOfMeasurement[qi] = [p_unit]
                onto.hasOriginalValue[qi].append(p_value_orig)

            elif len(p_value) == 2:
                qi = gr.QuantitativeValue()
                onto[p_name][someItem].append(qi)
                gr.hasMaxValue[qi].append(max(p_value))
                gr.hasMinValue[qi].append(min(p_value))
                gr.hasUnitOfMeasurement[qi] = [p_unit]
                onto.hasOriginalValue[qi].append(p_value_orig)

            else:
                for v in p_value:
                    qi = gr.QuantitativeValue()
                    onto[p_name][someItem].append(qi)
                    gr.hasValue[qi].append(v)
                    gr.hasUnitOfMeasurement[qi] = [p_unit]
                    onto.hasOriginalValue[qi].append(p_value_orig)
        else:
            qi = gr.QuantitativeValue()
            onto[p_name][someItem].append(qi)
            onto.hasOriginalValue[qi].append(p_value_orig)

    # data property
    elif p_value_orig:
        onto[p_name][someItem] = [p_value_orig]
    else:
        print("property %s could not be generated" % p_name)


def property_instance_gr(gr, p_name, p_unit, p_value, someItem, offering):
    # print('gr', p_name, p_unit, p_value, someItem)
    objectproperty_product = {}
    objectproperty_offering = {'hasEligibleQuantity': gr.QuantitativeValue}
    dataproperty_offering = {'hasCurrency': {'o': gr.PriceSpecification, 'p': gr.hasPriceSpecification},
                             'hasCurrencyValue': {'o': gr.PriceSpecification, 'p': gr.hasPriceSpecification}}

    # object property
    if ObjectProperty in gr[p_name].is_a:
        # specific case for manufacturer
        if p_name == 'hasManufacturer':
            organization = None
            for org in onto.search(iri='http://purl.org/goodrelations/v1#businessentity*'):
                if p_value == org.label[0] or p_value in org.altLabel:
                    organization = org
                    break
            if not organization:
                organization = gr.BusinessEntity(label=[p_value])
            gr[p_name][someItem] = [organization]
        elif p_name == 'hasBrand':
            brand = None
            for br in onto.search(iri='http://purl.org/goodrelations/v1#brand*'):
                if p_value == br.label[0] or p_value in br.altLabel:
                    brand = br
                    break
            if not brand:
                brand = gr.Brand(label=[p_value])
            gr[p_name][someItem] = [brand]
        else:
            object_product = objectproperty_product.get(p_name)
            object_offering = objectproperty_offering.get(p_name)
            if object_product:
                qi = object_product(label=p_value)
                gr[p_name][someItem] = [qi]

            elif object_offering:
                qi = object_offering(label=p_value)
                gr[p_name][offering] = [qi]

            else:
                print('property %s not created, update gr specific object dictionaries' % p_name)

    # data property
    else:
        obj_offering = dataproperty_offering.get(p_name)
        if obj_offering:
            if obj_offering.get('p')[offering]:
                specific_object_offering = obj_offering.get('p')[offering][0]
            else:
                specific_object_offering = obj_offering.get('o')()
                obj_offering.get('p')[offering] = [specific_object_offering]

            gr[p_name][specific_object_offering] = [p_value]

        else:
            gr[p_name][someItem] = [p_value]


def property_instance_schema(schemaorg, p_name, p_unit, p_value, someItem, offering):
    specific_objects_offering = {}

    # object property
    if ObjectProperty in schemaorg[p_name].is_a:
        if p_name == 'Availability':
            availability = None
            for av in schemaorg.ItemAvailability.instances():
                if p_value.split('/')[-1] == av.label[0]:
                    availability = av
                    break
            if not availability:
                availability = schemaorg.ItemAvailability(p_value.split('/')[-1], label=[p_value.split('/')[-1]])
            schemaorg[p_name][offering] = [availability]
        else:
            specific_object_offering = specific_objects_offering.get(p_name)
            if specific_object_offering:
                qi = specific_object_offering(label=p_value)
                schemaorg[p_name][offering] = [qi]
            else:
                print('property %s not created, update schema specific object dictionaries' % p_name)
    else:
        schemaorg[p_name][someItem] = [p_value]


def population(onto):
    print('Getting Namespaces...')
    gr = onto.get_namespace("http://purl.org/goodrelations/v1#")
    schemaorg = onto.get_namespace("http://schema.org/")
    mbse = onto.get_namespace("http://david.org/informationmodel.owl#")
    skos = onto.get_namespace("http://www.w3.org/2004/02/skos/core#")

    print('Reading Units Parsing Result...')
    df_units = pd.read_json(units_file)
    df_units = df_units.set_axis(col_df_units, axis='columns')

    print('Reading Property Mapping Result...')
    df_pp = pd.read_csv(pp_file, delimiter=";")
    if not set(col_df_pp_uv).issubset(df_pp.columns):
        print('The columns of the property mapping result file where modified')
        exit()

    print('Updating Vocabulary...')
    df_pp_uv = df_pp.loc[~pd.isna(df_pp['UserValidation']) & ((df_pp['Ontology'] == 'ECLASS') |
                                                              (pd.isna(df_pp['Ontology'])))].drop_duplicates(
        subset='RequestID')
    update_vocabulary(onto, gr, df_pp_uv)

    print('Generating Instances...')
    right = df_pp[['Source', 'ProductCategory', 'ProductClass']].drop_duplicates()
    df_pp_uv = df_pp.loc[~pd.isna(df_pp['UserValidation'])].drop_duplicates(subset='RequestID')
    df_units_r = pd.merge(df_units, right, on=['Source', 'ProductCategory'])
    generate_instances(onto, gr, mbse, schemaorg, skos, df_units_r, df_pp_uv)

    print('Saving World...')
    MyWorld.save()


if __name__ == '__main__':
    print('Loading Ontology...')
    MyWorld = World(filename="PCS/eclass11.sqlite3")
    onto = MyWorld.get_ontology("http://www.intelligent-match.de/eco11/").load()
    population(onto)
