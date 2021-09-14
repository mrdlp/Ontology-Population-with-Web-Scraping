from owlready2 import *


def edit_ontology(onto, mbse):
    bfo = get_ontology("http://purl.obolibrary.org/obo/bfo.owl").load()
    gr = onto.get_namespace("http://purl.org/goodrelations/v1#")
    schemaorg = onto.get_namespace("http://schema.org/")

    bfo_entity = IRIS['http://purl.obolibrary.org/obo/BFO_0000001']
    bfo_gdc = IRIS['http://purl.obolibrary.org/obo/BFO_0000031']
    bfo_site = IRIS['http://purl.obolibrary.org/obo/BFO_0000029']
    bfo_object = IRIS['http://purl.obolibrary.org/obo/BFO_0000030']
    bfo_me = IRIS['http://purl.obolibrary.org/obo/BFO_0000040']
    bfo_ic = IRIS['http://purl.obolibrary.org/obo/BFO_0000004']
    bfo_sdc = IRIS['http://purl.obolibrary.org/obo/BFO_0000020']
    bfo_quality = IRIS['http://purl.obolibrary.org/obo/BFO_0000019']
    bfo_re = IRIS['http://purl.obolibrary.org/obo/BFO_0000017']
    bfo_role = IRIS['http://purl.obolibrary.org/obo/BFO_0000023']
    bfo_disp = IRIS['http://purl.obolibrary.org/obo/BFO_0000016']
    bfo_process = IRIS['http://purl.obolibrary.org/obo/BFO_0000015']
    bfo_T1D = IRIS['http://purl.obolibrary.org/obo/BFO_0000038']

    onto.imported_ontologies.append(mbse)
    onto.imported_ontologies.append(bfo)

    # new classes
    with onto:
        class Webpage(mbse.information_concretization):
            namespace = mbse
            label = ['Webpage']

        class ItemAvailability(gr.QualitativeValue):
            namespace = schemaorg
            label = ['Item availability']

        class Availability(ObjectProperty):
            namespace = schemaorg
            domain = [schemaorg.Offer]
            range = [ItemAvailability]
            label = ['Availability']

        class hasOriginalValue(DatatypeProperty):
            domain = [gr.QuantitativeValue]
            label = ['Orignal Value']
            comment = [
                'This property serves to store the original value of the quantitative property extracted from the internet']

        class hasRole(ObjectProperty):
            label = ['has role']
            domain = [bfo_ic]
            range = [bfo_role]

        class realizes(ObjectProperty):
            label = ['realizes']
            domain = [bfo_process]
            range = [bfo_re]

        class EconomicGoodRole(bfo_role):
            label = ['Economic good role']

        class DispositionToProvideService(bfo_disp):
            label = ['Disposition to provide service']

        class Product(bfo_object):
            label = ['Product']
            hasRole = [EconomicGoodRole]

        class Service(bfo_process):
            label = ['Service']
            realizes = [DispositionToProvideService]

        class Agent(bfo_ic):
            label = ['Agent']

        class ECLASSType(ObjectProperty):
            label = ['ECLASS category']
            domain = [gr.ProductOrService]
            range = [Or([onto.Service, onto.Product])]

    # GR annotations
    gr.hasMPN.altLabel.append('mpn')
    gr.hasStockKeepingUnit.altLabel.append('sku')
    gr["hasGTIN-8"].altLabel.append('GTIN-8')
    gr["hasGTIN-14"].altLabel.append('GTIN-14')
    gr.hasBrand.altLabel.append('Brand')
    gr.hasCurrencyValue.altLabel.append('Price')
    gr.hasCurrency.altLabel.append('priceCurrency')

    # system and product or service
    mbse.system.is_a.append(bfo_entity)
    gr.ProductOrService.is_a.append(mbse.system)
    PS_EQ = Or([onto.hasRole.some(onto.EconomicGoodRole), onto.realizes.some(onto.DispositionToProvideService)])
    gr.ProductOrService.equivalent_to.append(PS_EQ)

    # generically dependent continuants
    gdc = [mbse.viewpoint, mbse.language, mbse.doc_format, mbse.information]
    for c in gdc:
        c.is_a.append(bfo_gdc)

    # information
    inf = [gr.Offering, gr.Brand, gr.PriceSpecification, gr.WarrantyScope, gr.WarrantyPromise, gr.TypeAndQuantityNode,
           gr.QuantitativeValue, gr.QualitativeValue]
    for c in inf:
        c.is_a.append(mbse.information)

    # site
    gr.Location.is_a.append(bfo_site)

    # material entity
    mbse.information_carrier.is_a.append(bfo_me)

    # agents
    agents = [gr.BusinessEntity, mbse.organization, mbse.organizational_unit, mbse.actor]
    for c in agents:
        c.is_a.append(onto.Agent)

    # information concretization
    mbse.information_concretization.is_a.append(bfo_quality)

    # role
    mbse.role.equivalent_to.append(bfo_role)
    gr.BusinessEntityType.is_a.append(bfo_role)

    # processes
    processes = [gr.BusinessFunction, gr.DeliveryMethod, gr.PaymentMethod, mbse.event, mbse.project, mbse.task]
    for c in processes:
        c.is_a.append(bfo_process)

    # temporal region 1D
    gr.DayOfWeek.is_a.append(bfo_T1D)
    gr.OpeningHoursSpecification.is_a.append(bfo_T1D)

    # ECLASS TAX GEN
    for c in onto.classes():
        if c.hierarchyCode:
            generic_class = [gc for gc in c.subclasses() if '-gen' in gc.name][0]
            if int(c.hierarchyCode[0]) < 16000000:
                generic_class.is_a.append(onto.Service)
                if int(c.hierarchyCode[0]) % 1000000 == 0:
                    c.is_a.append(bfo_process)
            else:
                generic_class.is_a.append(onto.Product)
                if int(c.hierarchyCode[0]) % 1000000 == 0:
                    c.is_a.append(bfo_object)

    # individuals
    mbse.language('HTML', label='HTML')
    mbse.viewpoint('Procurement', label='Procurement')
    mbse.person('Miguel', label='Miguel', has=[mbse.Procurement])
    schemaorg.ItemAvailability('BackOrder', label='BackOrder')
    schemaorg.ItemAvailability('Discontinued', label='Discontinued')
    schemaorg.ItemAvailability('InStock', label='InStock')
    schemaorg.ItemAvailability('InStoreOnly', label='InStoreOnly')
    schemaorg.ItemAvailability('LimitedAvailability', label='LimitedAvailability')
    schemaorg.ItemAvailability('OnlineOnly', label='OnlineOnly')
    schemaorg.ItemAvailability('OutOfStock', label='OutOfStock')
    schemaorg.ItemAvailability('PreOrder', label='PreOrder')
    schemaorg.ItemAvailability('PreSale', label='PreSale')
    schemaorg.ItemAvailability('SoldOut', label='SoldOut')

    # save file
    default_world.set_backend(filename="PCS/eclass11.sqlite3")
    default_world.save()


if __name__ == '__main__':
    print('Editing Ontology...')
    onto = get_ontology("PCS/eco11.rdf").load()
    mbse = get_ontology("PCS/mbse-information-model.owl").load()
    edit_ontology(onto, mbse)
