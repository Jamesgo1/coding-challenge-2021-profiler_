from processor_classes.mla_profiling import ProfileParameterCreator
from tests import pkl

ppc = ProfileParameterCreator()
t2 = ppc.create_parameters_from_mla_data()
pkl.pickle_w(t2, "profiles")
