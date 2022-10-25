import r from '@hat-open/renderer';
import * as u from '@hat-open/util';
import * as juggler from '@hat-open/juggler';


import '../src_scss/main.scss';


type Status = 'STOPPED' | 'DELAYED' | 'STARTING' | 'RUNNING' | 'STOPPING';

type Component = {
    id: number,
    name: string,
    delay: number,
    revive: boolean,
    status: Status
};


const defaultState = {
    remote: null
};


let app: juggler.Application | null = null;


function main() {
    const root = document.body.appendChild(document.createElement('div'));
    r.init(root, defaultState, vt);
    app = new juggler.Application('remote');
}


function vt(): u.VNode {
    const remote = r.get('remote');
    if (remote == null)
        return ['div.orchestrator'];

    const components = r.get('remote', 'components') as Component[];
    return ['div.orchestrator',
        ['table',
            ['thead',
                ['tr',
                    ['th.col-component', 'Component'],
                    ['th.col-delay', 'Delay'],
                    ['th.col-revive', 'Revive'],
                    ['th.col-status', 'Status'],
                    ['th.col-action', 'Action']
                ]
            ],
            ['tbody', components.map(component =>
                ['tr',
                    ['td.col-component', component.name],
                    ['td.col-delay', String(component.delay)],
                    ['td.col-revive',
                        ['input', {
                            props: {
                                type: 'checkbox',
                                checked: component.revive
                            },
                            on: {
                                change: (evt: any) => {
                                    if (!app)
                                        return;
                                    app.send('revive', {
                                        id: component.id,
                                        value: evt.target.checked
                                    });
                                }
                            }}
                        ]
                    ],
                    ['td.col-status', component.status],
                    ['td.col-action',
                        ['button', {
                            props: {
                                title: 'Stop',
                                disabled: u.contains(
                                    component.status, ['STOPPING', 'STOPPED'])
                            },
                            on: {
                                click: () => {
                                    if (!app)
                                        return;
                                    app.send('stop', {
                                        id: component.id
                                    });
                                }
                            }},
                            ['span.fa.fa-times']
                        ],
                        ['button', {
                            props: {
                                title: 'Start',
                                disabled: u.contains(
                                    component.status,
                                    ['STARTING', 'RUNNING', 'STOPPING'])
                            },
                            on: {
                                click: () => {
                                    if (!app)
                                        return;
                                    app.send('start', {
                                        id: component.id
                                    });
                                }
                            }},
                            ['span.fa.fa-play']
                        ]
                    ]
                ]
            )]
        ]
    ];
}


window.addEventListener('load', main);
(window as any).r = r;
(window as any).u = u;
