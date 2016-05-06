from pip._vendor.pkg_resources import Requirement, RequirementParseError
try:
    from pip.utils import get_installed_distributions # pip 6.0
except ImportError:
    from pip.util import get_installed_distributions  # pip 1.5.x
from warnings import warn
import types


"""
This package attempts to pull all the Python library imports and their
version numbers from a session's globals. These are called implicit
requirements. It also provides a function for merging implicit and explicit
requirement into one requirements list. Both return lists of requirement
instances from the pip library.

Example:

    from sklearn.svm import SVR as svr
    from yhat import requirements
    import pandas as pd

    print requirements.implicit(globals())
    print requirements.merge(globals(), "scikit-learn==0.15.2")
"""

def _get_package_name(obj):
    """Returns the package name (e.g. "sklearn") for a Python object"""
    try:
        if isinstance(obj, types.ModuleType):
            return obj.__package__.split(".")[0]
        elif isinstance(obj, types.TypeType):
            return obj.__module__.split(".")[0]
        elif isinstance(obj, types.ObjectType):
            return obj.__class__.__module__.split(".")[0]
        else:
            return None
    except:
        return None

def initializeRequirements(model):
    requirements = {
        'modelSpecified': [],
        'required': [],
        'autodetected': []
    }
    user_reqs = getattr(model, "REQUIREMENTS", "")
    if isinstance(user_reqs, basestring):
        user_reqs = [r for r in user_reqs.splitlines() if r]
    if user_reqs:
        for r in user_reqs:
            try:
                if r[:4] != 'yhat':
                    requirements['modelSpecified'].append(Requirement.parse(r))
            except RequirementParseError:
                if r[:3] == 'git' or r[:9] == 'ssh://git':
                    requirements['modelSpecified'].append(r)
                else:
                    print 'Package ' + r + ' was not recognized as a valid package.'
            except:
                print "Unexpected error:", sys.exc_info()[0]
                raise

    # Always add yhat package to required with installed version.
    import yhat
    yhatReq = Requirement.parse('yhat==%s' % yhat.__version__)
    requirements['required'].append(yhatReq)

    return requirements

def getImplicitRequirements(model, session):
    requirements = initializeRequirements(model)
    requirements = implicit(session, requirements)
    printRequirements(requirements)
    return bundleRequirments(requirements)

def getExplicitRequirmets(model, session):
    requirements = initializeRequirements(model)
    printRequirements(requirements)
    return bundleRequirments(requirements)

def printRequirements(requirements):
    for cat, reqList in requirements.items():
        if reqList:
            if cat == "required":
                print "required packages"
            elif cat == "modelSpecified":
                print "model specified requirements"
            elif cat == "autodetected":
                print "autodetected packages"
            for r in reqList:
                if "==" not in str(r) and str(r)[:3] != 'git':
                    r = r + " (warning: unversioned)"
                print " [+]", r

def bundleRequirments(requirements):
    """
    Put the requirements into a structure for the bundle
    """
    reqList = []
    mergedReqs = merge(requirements)
    for reqs in requirements.itervalues():
        if reqs:
            for r in reqs:
                reqList.append(r)
    bundleString = "\n".join(
        str(r) for r in reqList
    )

    return bundleString

def implicit(session, requirements):
    """
    Returns a list of Requirement instances for all the library dependencies
    of a given session. These are matched using the contents of "top_level.txt"
    metadata for all package names in the session.
    """
    package_names = [_get_package_name(g) for g in session.values()]
    package_names = set(filter(None, package_names))

    reqs = {}
    for d in get_installed_distributions():
        for top_level in d._get_metadata("top_level.txt"):
            if top_level in package_names:
                # Sanity check: if a distribution is already in our
                # requirements, make sure we only keep the latest version.
                if d.project_name in reqs:
                    reqs[d.project_name] = max(reqs[d.project_name], d.version)
                else:
                    reqs[d.project_name] = d.version
    requirements['autodetected'] = [Requirement.parse('%s==%s' % r) for r in reqs.items() if r[0] != 'yhat']


    return requirements


def merge(requirements):
    """
    Merges autodetected and explicit requirements together. Autodetected
    requirements are pulled out the user's session (i.e. globals()).
    Explicit requirements are provided directly by the user. This
    function reconciles them and merges them into one set of requirements.
    Warnings are given to the user in case of version mismatch or modules
    that do not need to be required explicitly.
    """
    implicit_dict = {}
    for r in requirements['autodetected']:
        implicit_dict[r.project_name] = r

    explicit_dict = {}
    for r in requirements['modelSpecified']:
        if type(r) != str:
            explicit_dict[r.project_name] = r

    for project_name, exp_req in explicit_dict.items():
        # To be polite, we keep the explicit dependencies and add the implicit
        # ones to them. We respect versions on the former, except in the case
        # of yhat, which should be the installed version.
        if project_name in implicit_dict:
            imp_req = implicit_dict[project_name]
            if exp_req == imp_req:
                warn(
                    "Dependency %s found implicitly. It can be removed "
                    "from REQUIREMENTS." % exp_req
                )
                requirements['autodetected'].remove(imp_req)
            elif project_name == "yhat":
                warn(
                    "Dependency yhat can be removed form REQUIREMENTS. "
                    "It is required and added for you."
                )
                requirements['autodetected'].remove(imp_req)
                requirements['modelSpecified'].remove(exp_req)
            else:
                warn(
                    "Dependency %s specified in REQUIREMENTS, but %s is "
                    "installed. Using the former." % (exp_req, imp_req)
                )
                requirements['autodetected'].remove(imp_req)
                requirements['autodetected'].remove(exp_req)


    return requirements
