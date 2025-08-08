# -*- coding: utf-8 -*-
{
    'name': "tower_london",

    'summary': """
        test tower london""",

    'description': """
        test tower london
    """,

    'author': "MajdWannous",
    'website': "https://www.madwannous.com",

    'category': 'Uncategorized',
    'version': '0.1',
    'depends': ['base', 'account', 'web'],


    'data': [
        'security/groups.xml',
        'security/record_rules.xml',
        'security/ir.model.access.csv',
        'report/patient_report.xml',
        'report/clinic_report.xml',
        'report/finance_report.xml',
        'views/views.xml',
        'views/action_dashboard.xml',
        'data/account_data.xml',

    ],
    'assets' : {
         'web.report_assets_common': [
             'tower_london/static/src/img/logo.png',
            ],
        'web.assets_backend' : [
            'tower_london/static/src/components/dashboard.js',
            'tower_london/static/src/components/chart.js',
            'tower_london/static/src/components/dashboard.xml',
        ],


    },

}