# Workflow Report: order-batch2-1759620852-11

## Description

Execution Info:
  WorkflowId            order-batch2-1759620852-11
  RunId                 0199b193-6e0c-7ce2-9e07-8c119bf019b5
  Type                  OrderWorkflow
  Namespace             default
  TaskQueue             orders-tq
  AssignedBuildId        
  StartTime             1 minute ago
  CloseTime             1 minute ago
  ExecutionTime         1 minute ago
  SearchAttributes      map[BuildIds:metadata:{key:"encoding"  value:"json/plain"}  metadata:{key:"type"  value:"KeywordList"}  data:"[\"unversioned\",\"unversioned:825a6b987df39d74d5264902d4d8a8af\"]"]
  StateTransitionCount  17
  HistoryLength         17
  HistorySize           3359
  RootWorkflowId        order-batch2-1759620852-11
  RootRunId             0199b193-6e0c-7ce2-9e07-8c119bf019b5
Extended Execution Info:
  CancelRequested    false
  RunExpirationTime  1 minute ago
  OriginalStartTime  1 minute ago

Results:
  RunTime         10.69s
  Status          COMPLETED
  Result          {"errors":["module 'temporalio.workflow' has no attribute 'await_typed'"],"order_id":"batch2-1759620852-11","status":"failed","step":"MANUAL_REVIEW"}
  ResultEncoding  json/plain


## Event History

Progress:
  ID           Time                     Type           
    1  2025-10-04T23:34:13Z  WorkflowExecutionStarted  
    2  2025-10-04T23:34:13Z  WorkflowTaskScheduled     
    3  2025-10-04T23:34:13Z  WorkflowTaskStarted       
    4  2025-10-04T23:34:13Z  WorkflowTaskCompleted     
    5  2025-10-04T23:34:13Z  ActivityTaskScheduled     
    6  2025-10-04T23:34:14Z  ActivityTaskStarted       
    7  2025-10-04T23:34:14Z  ActivityTaskCompleted     
    8  2025-10-04T23:34:14Z  WorkflowTaskScheduled     
    9  2025-10-04T23:34:14Z  WorkflowTaskStarted       
   10  2025-10-04T23:34:14Z  WorkflowTaskCompleted     
   11  2025-10-04T23:34:14Z  ActivityTaskScheduled     
   12  2025-10-04T23:34:23Z  ActivityTaskStarted       
   13  2025-10-04T23:34:23Z  ActivityTaskCompleted     
   14  2025-10-04T23:34:23Z  WorkflowTaskScheduled     
   15  2025-10-04T23:34:23Z  WorkflowTaskStarted       
   16  2025-10-04T23:34:23Z  WorkflowTaskCompleted     
   17  2025-10-04T23:34:23Z  WorkflowExecutionCompleted

Results:
  Status          COMPLETED
  Result          {"errors":["module 'temporalio.workflow' has no attribute 'await_typed'"],"order_id":"batch2-1759620852-11","status":"failed","step":"MANUAL_REVIEW"}
  ResultEncoding  json/plain
