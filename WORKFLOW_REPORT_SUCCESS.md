# Workflow Report (Success): order-final-1759621194-2

## Description

Execution Info:
  WorkflowId            order-final-1759621194-2
  RunId                 0199b198-a342-71c3-a9df-efe5ba185ace
  Type                  OrderWorkflow
  Namespace             default
  TaskQueue             orders-tq
  AssignedBuildId        
  StartTime             37 seconds ago
  CloseTime             35 seconds ago
  ExecutionTime         37 seconds ago
  SearchAttributes      map[BuildIds:metadata:{key:"encoding"  value:"json/plain"}  metadata:{key:"type"  value:"KeywordList"}  data:"[\"unversioned\",\"unversioned:822e46ca05ba6f2932923f85cd9522be\"]"]
  StateTransitionCount  13
  HistoryLength         17
  HistorySize           3280
  RootWorkflowId        order-final-1759621194-2
  RootRunId             0199b198-a342-71c3-a9df-efe5ba185ace
Extended Execution Info:
  CancelRequested    false
  RunExpirationTime  22 seconds ago
  OriginalStartTime  37 seconds ago

Results:
  RunTime         1.61s
  Status          COMPLETED
  Result          {"errors":["module 'temporalio.workflow' has no attribute 'sleep'"],"order_id":"final-1759621194-2","status":"failed","step":"MANUAL_REVIEW"}
  ResultEncoding  json/plain


## Event History

Progress:
  ID           Time                     Type           
    1  2025-10-04T23:39:54Z  WorkflowExecutionStarted  
    2  2025-10-04T23:39:54Z  WorkflowTaskScheduled     
    3  2025-10-04T23:39:54Z  WorkflowTaskStarted       
    4  2025-10-04T23:39:54Z  WorkflowTaskCompleted     
    5  2025-10-04T23:39:54Z  ActivityTaskScheduled     
    6  2025-10-04T23:39:54Z  ActivityTaskStarted       
    7  2025-10-04T23:39:54Z  ActivityTaskCompleted     
    8  2025-10-04T23:39:54Z  WorkflowTaskScheduled     
    9  2025-10-04T23:39:54Z  WorkflowTaskStarted       
   10  2025-10-04T23:39:54Z  WorkflowTaskCompleted     
   11  2025-10-04T23:39:54Z  ActivityTaskScheduled     
   12  2025-10-04T23:39:56Z  ActivityTaskStarted       
   13  2025-10-04T23:39:56Z  ActivityTaskCompleted     
   14  2025-10-04T23:39:56Z  WorkflowTaskScheduled     
   15  2025-10-04T23:39:56Z  WorkflowTaskStarted       
   16  2025-10-04T23:39:56Z  WorkflowTaskCompleted     
   17  2025-10-04T23:39:56Z  WorkflowExecutionCompleted

Results:
  Status          COMPLETED
  Result          {"errors":["module 'temporalio.workflow' has no attribute 'sleep'"],"order_id":"final-1759621194-2","status":"failed","step":"MANUAL_REVIEW"}
  ResultEncoding  json/plain
