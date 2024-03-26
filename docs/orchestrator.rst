Orchestrator
============

Orchestrator is the component responsible for starting and monitoring execution
of other Hat components and their dependencies on a single machine. This
component is used as simple cross-platform replacement for default OS
service/daemon manager. Additionally, Orchestrator provides web-based user
interface for monitoring and controlling configured components. Orchestrator
is distributed as `hat-orchestrator` package.


Running
-------

By installing Orchestrator from `hat-orchestrator` package, executable
`hat-orchestrator` becomes available and can be used for starting this
component.

.. program-output:: python -m hat.orchestrator --help


Component orchestration
-----------------------

Based on configuration parameters, Orchestrator spawns new child processes
representing other components. Execution of child processes is monitored and
their standard output and errors are logged. Once Orchestrator's process
terminates, all spawned child processes are also terminated.

Each component is configured with these parameters:

* `name`

  Name used for component identification by the Orchestrator.

* `args`

  Command line arguments (including binary name) used when starting
  component's process.

* `stdin`

  Optional data passed to component's standard input. If data exists,
  standard input is closed after data is written.

* `delay`

  Startup delay in seconds applied only upon first component startup.

* `revive`

  If this property is set to true, Orchestrator will restart component's
  process as soon as it terminates.

* `auto_start`

  If this property is set to false, Orchestrator will skip component
  startup during orchestrator startup.

Automatic revival of stopped component includes constant delay (0.5 seconds)
which stops overly zealous repetitive spawning of constantly closing process.

Termination of each component is done by sending SIGINT signal (or
CTRL_BREAK_EVENT on Windows) to component's process. If process doesn't finish
during timeout period (5 seconds) after sending signal, process should be
forcefully terminated by sending SIGKILL (or calling TerminateProcess on
Windows).

Each component's output is redirected to Orchestrator's output. Orchestrator's
standard input is non deterministically forwarded to components without stdin
data.


Component states and actions
----------------------------

During it's lifetime, component can be in one of following states:

* STOPPED

  State representing component without associated running process.
  If startup delay is not set, this is initial state.

* DELAYED

  Temporary state which occurs only once if component is configured with
  startup delay time. This state initial state and can not be entered
  from any other state. Usual transition from this state is to STARTING
  state, or to STOPPED state if stop action is issued.

* STARTING

  State representing preparation and starting of new process.

* RUNNING

  State of component with associated running process.

* STOPPING

  State representing currently active termination procedure involving
  'soft' and 'hard' process termination actions.

States STARTING and STOPPING are considered transitional states. Those states
can not be interrupted by user actions. All actions which are registered during
these states are buffered and only last action is executed once component exits
these states. In all other states, actions are executed based on current state
and are not queued for sequential execution.

Component implementation exposes this externally available actions:

* start

  If current state of component is STOPPED or DELAYED, this action starts
  component's startup procedure (it is expected that component will
  transit to STARTING state). If current state is RUNNING, this action
  has no effect.

* stop

  If current state of component is RUNNING, this action stops component
  execution by starting previously described termination procedure (it is
  expected that component will transit to STOPPING state). If current
  state is DELAYED, this component transits directly to STOPPED state.
  For STOPPED state, this action is ignored.

* change revive

  If current state of component is STOPPED and revive is set to true,
  component's startup procedure is implicitly called.

Usual transition between states if not actions are performed is `DELAYED or
STOPPED > STARTING > RUNNING > STOPPING > STOPPED > STARTING > ...` with
exceptions:

* DELAYED is initial state if component delay is set. otherwise initial
  state is STOPPED
* state STARTING can transit directly to STOPPED state if error occurs
  during process startup procedure
* transition from STOPPED to STARTING occurs if `revive` flag is set


Web user interface
------------------

Orchestrator provides web user interface as primary way of user's monitoring
and controlling of components' process execution. Functionality of this
interface can be split into backend and frontend implementation. Backend
is part of Orchestrator's process and frontend is implemented as single page
application running in browser. Communication between frontend and backend
is based on juggler communication protocol.

Monitoring functionality provides real time information of all configured
components and their current state.

Control functionality enables user to change value of revive flag, start or
stop each component. This functionality directly translates to calling of
component's start, stop and change revive actions.


Server state
''''''''''''

Juggler server state is used for providing current state of all components.

State structure is defined by JSON schema
``hat-orchestrator://juggler.yaml#/$defs/state``.


Request/response
''''''''''''''''

Juggler request/response communication is used primary for enabling user
control of configured components.

Request data structures are defined by JSON schema
``hat-orchestrator://juggler.yaml#/$defs/request``.

In case of successful request execution, response data is ``null``.


Possible future improvements
----------------------------

* configurable revive delay
* configurable termination timeout
* console user interface based on prompt-toolkit

    * switching between component outputs
    * deterministic redirecting standard input to specific component
    * alternative to web user interface

* additional features of web user interface

    * real-time logging of component output
    * additional information on running process status (total running time,
      pid, ...), revive counter, ...

* optional connection to monitor/event server

    * mapping of current status to events
    * listening for control events


Juggler definitions
-------------------

.. literalinclude:: ../schemas_json/juggler.yaml
    :language: yaml
