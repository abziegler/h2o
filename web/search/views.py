import requests

from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import render
from django.urls import reverse

from test.test_helpers import check_response
from main.utils import looks_like_citation, looks_like_casename
from .models import SearchIndex

type_param_to_category = {'cases': 'case', 'casebooks': 'casebook', 'users': 'user'}


def search(request):
    """
        Search page.

        Given:
        >>> capapi_mock, client, casebook_factory = [getfixture(i) for i in ['capapi_mock', 'client', 'casebook_factory']]
        >>> casebooks = [casebook_factory(tempcollaborator_set__user__verified_professor=True) for i in range(3)]
        >>> url = reverse('search')
        >>> SearchIndex().create_search_index()

        Show all casebooks by default:
        >>> check_response(client.get(url), content_includes=[c.title for c in casebooks])

        See SearchIndex._search tests for more specific tests.

        This view is also used for searching by citation for cases to import from CAPAPI. The CAP version kicks in if
        we provide 'type': 'cases', 'partial': 'true', and a query that starts and ends in digits:
        >>> check_response(
        ...     client.get(url, {'type': 'cases', 'q': '722 F.3d 1229', 'partial': 'true'}),
        ...     content_includes=['data-result-id="1" data-result-type="capapi/case"', '1-800 Contacts, Inc. v. Lens.Com, Inc.'],
        ... )

        TODO: add test for FLP search
    """
    # read query parameters
    category = type_param_to_category.get(request.GET.get('type', None), 'casebook')
    try:
        page = int(request.GET.get('page'))
    except (TypeError, ValueError):
        page = 1
    query = request.GET.get('q')
    partial = request.GET.get('partial') == 'true'

    # If searching for a case from add-resource modal, try to get it from CAP then FLP:
    if category == 'case' and partial:

        # Query CAP API and then FLP API if user enters something citation-like
        if looks_like_citation(query):

            # First try CAP API
            response = requests.get(settings.CAPAPI_BASE_URL+"cases/", {"cite": query})
            results = response.json()['results']
            if len(results) > 0:
                results = Paginator(results, 10).get_page(1)
                results.from_capapi = True
                counts = facets = None

            # If CAP can't find it, try FLP
            else:
                # TODO add FLP URL to settings
                headers = {'Authorization': f'Token {settings.FLP_API_KEY}'}
                response = requests.get(settings.FLP_BASE_URL+f"search/?citation={query}", headers=headers)
                results = response.json()['results']
                if len(results) > 0:
                    results = Paginator(results, 10).get_page(1)
                    for result in results:
                        result['dateFiled'] = result['dateFiled'].split('T')[0]
                    results.from_flp = True
                    counts = facets = None


        # Query CAP API and then FLP API if user enters something casename-like:
        elif looks_like_casename(query):

            # First try CAP:
            response = requests.get(settings.CAPAPI_BASE_URL + "cases/", {"name_abbreviation": query})
            results = response.json()['results']
            if len(results) > 0:
                results = Paginator(results, 10).get_page(1)
                results.from_capapi = True
                counts = facets = None

            # If CAP can't find it, try FLP
            else:
                headers = {'Authorization': f'Token {settings.FLP_API_KEY}'}
                response = requests.get(settings.FLP_BASE_URL+f"search/?case_name={query}", headers=headers)
                results = response.json()['results']
                if len(results) > 0:
                    results = Paginator(results, 10).get_page(1)
                    for result in results:
                        result['dateFiled'] = result['dateFiled'].split('T')[0]
                    results.from_flp = True
                    counts = facets = None

    # else query postgres:
    else:
        filters = {}
        author = request.GET.get('author')
        school = request.GET.get('school')
        if author:
            filters['attribution'] = author
        if school:
            filters['affiliation'] = school

        results, counts, facets = SearchIndex.search(
            category,
            page=page,
            query=query,
            filters=filters,
            facet_fields=['attribution', 'affiliation'],
            order_by=request.GET.get('sort')
        )
        results.from_capapi = False
        results.from_FLP = False

    if partial:
        return render(request, 'search/results.html', {
            'results': results,
            'category': category,
            'path': reverse('search'),
        })
    else:
        return render(request, 'search/show.html', {
            'results': results,
            'counts': counts,
            'facets': facets,
            'category': category,
        })
