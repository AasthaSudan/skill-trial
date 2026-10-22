"""Create the first reviewed-ready advanced and Spring Boot content pack.

Generated YAML remains a draft until the regular executable validation and
independent admin review/publish workflow approves it.
"""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'content' / 'challenges'

TASKS = [
    {
        'slug': 'window-triple-maximum', 'title': 'Best three-step window',
        'statement': 'Return the greatest sum of any contiguous window of exactly three integers. Return null when fewer than three values are supplied. The input can contain negative numbers and up to 100,000 values.',
        'competencies': ['collections', 'algorithms', 'edge_cases'],
        'inputs': [[4, -2, 5, 1, 9], [1, 2], [-8, -1, -3, -2], [7, 7, 7, 1], [1000000, -1000000, 500000, 700000]],
        'expected': [15, None, -6, 21, 500000],
        'python': 'def solve(nums):\n    if len(nums) < 3:\n        return None\n    current=sum(nums[:3]); best=current\n    for i in range(3,len(nums)):\n        current += nums[i]-nums[i-3]\n        best=max(best,current)\n    return best',
        'javascript': 'function solve(nums) { if(nums.length<3)return null; let s=nums[0]+nums[1]+nums[2],best=s; for(let i=3;i<nums.length;i++){s+=nums[i]-nums[i-3];if(s>best)best=s;} return best; }',
        'java': 'class Solution { public static Object solve(int[] nums) { if(nums.length<3)return null; long sum=(long)nums[0]+nums[1]+nums[2],best=sum; for(int i=3;i<nums.length;i++){sum+=(long)nums[i]-nums[i-3];best=Math.max(best,sum);} return best; } }',
    },
    {
        'slug': 'longest-rising-run', 'title': 'Longest rising run',
        'statement': 'Return the length of the longest contiguous strictly increasing run. Equal neighboring values break a run. Empty input returns zero. The algorithm should scan the input once.',
        'competencies': ['collections', 'algorithms', 'edge_cases'],
        'inputs': [[1, 2, 2, 3, 4], [], [-5, -4, -3, -10, -8], [9, 8, 7], [3, 4, 5, 6]],
        'expected': [3, 0, 3, 1, 4],
        'python': 'def solve(nums):\n    if not nums:return 0\n    best=current=1\n    for i in range(1,len(nums)):\n        current=current+1 if nums[i]>nums[i-1] else 1\n        best=max(best,current)\n    return best',
        'javascript': 'function solve(nums) { if(!nums.length)return 0; let best=1,current=1; for(let i=1;i<nums.length;i++){current=nums[i]>nums[i-1]?current+1:1;best=Math.max(best,current);} return best; }',
        'java': 'class Solution { public static Object solve(int[] nums) { if(nums.length==0)return 0; int best=1,current=1; for(int i=1;i<nums.length;i++){current=nums[i]>nums[i-1]?current+1:1;best=Math.max(best,current);} return best; } }',
    },
    {
        'slug': 'nondecreasing-removals', 'title': 'Fewest removals for ordered data',
        'statement': 'Return the minimum number of elements to remove so the remaining values, kept in their original order, are non-decreasing. Equal values may remain. Use an algorithm suitable for 100,000 values.',
        'competencies': ['collections', 'algorithms', 'edge_cases'],
        'inputs': [[4, 2, 3, 1, 5], [1, 2, 3], [3, 3, 2, 2, 1], [], [10, 9, 2, 5, 3, 7, 101, 18]],
        'expected': [2, 0, 3, 0, 4],
        'python': 'from bisect import bisect_right\ndef solve(nums):\n    tails=[]\n    for x in nums:\n        i=bisect_right(tails,x)\n        if i==len(tails):tails.append(x)\n        else:tails[i]=x\n    return len(nums)-len(tails)',
        'javascript': 'function solve(nums) { const tails=[]; for(const x of nums){let lo=0,hi=tails.length;while(lo<hi){const m=(lo+hi)>>1;if(tails[m]<=x)lo=m+1;else hi=m;}tails[lo]=x;} return nums.length-tails.length; }',
        'java': 'class Solution { public static Object solve(int[] nums) { int[] tails=new int[nums.length]; int n=0; for(int x:nums){int lo=0,hi=n;while(lo<hi){int m=(lo+hi)>>>1;if(tails[m]<=x)lo=m+1;else hi=m;}tails[lo]=x;if(lo==n)n++;} return nums.length-n; } }',
    },
    {
        'slug': 'closest-distinct-gap', 'title': 'Closest distinct values',
        'statement': 'Return the smallest absolute difference between any two distinct values. Repeated copies of one value do not form a pair. Return null when fewer than two distinct values exist. Integer endpoints may be far apart.',
        'competencies': ['collections', 'algorithms', 'edge_cases'],
        'inputs': [[8, 1, 5, 12], [4, 4, 10], [7], [-2147483648, 2147483647], [0, 0, 0]],
        'expected': [3, 6, None, 4294967295, None],
        'python': 'def solve(nums):\n    vals=sorted(set(nums))\n    if len(vals)<2:return None\n    return min(vals[i]-vals[i-1] for i in range(1,len(vals)))',
        'javascript': 'function solve(nums) { const vals=[...new Set(nums)].sort((a,b)=>a-b); if(vals.length<2)return null; let best=Infinity; for(let i=1;i<vals.length;i++)best=Math.min(best,vals[i]-vals[i-1]); return best; }',
        'java': 'class Solution { public static Object solve(int[] nums) { java.util.TreeSet<Integer> values=new java.util.TreeSet<>(); for(int x:nums)values.add(x); if(values.size()<2)return null; long best=Long.MAX_VALUE; Integer previous=null; for(int x:values){if(previous!=null)best=Math.min(best,(long)x-previous);previous=x;} return best; } }',
    },
]

SCENARIOS = [
    ('transaction-rollback', 'A failed order must roll back', 'A service writes an order and then calls a payment provider. The payment operation can fail after the write. Make the transaction boundary explicit and preserve correct rollback behavior.', ['services','persistence','transactions'], [
        ('boundary', 'Where should the transaction usually begin?', [('Around the service operation that owns the whole write unit', True), ('Only around the controller serialization', False), ('Only around the repository read', False)]),
        ('proxy', 'A @Transactional method is called from another method on the same bean. What is the key risk?', [('The proxy may be bypassed, so transaction advice may not run', True), ('Spring starts two network requests automatically', False), ('The database changes to read-only mode', False)]),
        ('rollback', 'A checked exception is thrown after a write. What makes rollback behavior reliable?', [('Declare the intended rollback rule, for example rollbackFor, and test the transaction boundary', True), ('Catch and ignore every exception in the controller', False), ('Assume every exception type always triggers rollback', False)]),
    ]),
    ('validated-api-boundary', 'Validate the request at the boundary', 'An API accepts a customer name and a positive quantity. Invalid requests must not reach business services, and callers need a consistent validation response.', ['rest_apis','validation','exceptions'], [
        ('dto', 'Where should the input constraints live?', [('On a request DTO with constraints such as @NotBlank and @Positive', True), ('Only in a database error handler', False), ('In a comment above the controller method', False)]),
        ('trigger', 'How does a controller request bean-validation for a request body?', [('Use @Valid (or @Validated where applicable) on the request parameter', True), ('Add @Transactional to the DTO', False), ('Use @Autowired on every field', False)]),
        ('response', 'How should validation errors be exposed?', [('Map field errors to a stable 4xx response without leaking internals', True), ('Return HTTP 200 with a Java stack trace', False), ('Silently replace invalid values with arbitrary defaults', False)]),
    ]),
    ('exception-contract', 'Keep the error contract stable', 'Several controllers currently catch broad exceptions and return success-shaped responses. Clients need reliable HTTP status codes and safe, actionable error bodies.', ['rest_apis','exceptions'], [
        ('mapping', 'Where is a shared HTTP exception mapping best expressed?', [('@RestControllerAdvice with narrow @ExceptionHandler methods', True), ('A static initializer in every entity', False), ('A catch-all that returns HTTP 200', False)]),
        ('specificity', 'How should unexpected internal failures be handled?', [('Log a correlation identifier server-side and return a generic 5xx body', True), ('Return the exception message and stack trace to every caller', False), ('Convert every failure to a validation 400', False)]),
        ('domain', 'A requested entity does not exist. Which response is usually the clearest contract?', [('A deliberate 404 mapping for the domain not-found case', True), ('A 200 response containing null', False), ('A 500 for all missing records', False)]),
    ]),
    ('service-proxy-boundary', 'Keep framework proxy boundaries real', 'A service relies on transactions and method security. A same-class call appears to work locally, while calls through the injected bean behave differently.', ['services','transactions'], [
        ('selfcall', 'Why can same-instance calls skip declarative advice?', ('Calls made with this.method bypass the proxy intercepting the bean', 'Java annotations execute themselves at bytecode runtime', 'The proxy only wraps repository interfaces')),
        ('design', 'What is the clearest repair when a cross-method boundary needs advice?', ('Move the advised operation behind an injected bean/proxy boundary or redesign the unit of work', 'Add more annotations to the same private method', 'Make the method static')),
        ('verify', 'How should the boundary be confirmed?', ('Exercise the operation through the Spring context and verify committed and rolled-back database state', 'Call the method directly on new Service()', 'Check only that the application context starts')),
    ]),
    ('idempotent-api-write', 'Make retried API writes safe', 'A client retries a POST after a timeout and the server may have committed the first request. Prevent duplicate orders while returning the original outcome for a retry with the same idempotency key.', ['rest_apis','services','persistence','transactions'], [
        ('key', 'Where should the idempotency key be enforced?', [('Persist it under a unique constraint scoped to the caller and operation', True), ('Keep it only in a controller field', False), ('Treat every retry as a new order', False)]),
        ('atomicity', 'How should key registration and the business write relate?', [('Make the key claim and order result durable atomically, handling a concurrent unique-key conflict by loading the existing result', True), ('Commit the key first and never recover if the order write fails', False), ('Use an in-memory map that disappears on restart', False)]),
        ('replay', 'What should a matching retry receive?', [('The stored outcome for the same request; reject reuse of the key for a different payload', True), ('A second order with a different identifier', False), ('A success response before checking the stored request', False)]),
    ]),
    ('jpa-read-boundary', 'Keep JPA reads bounded', 'An endpoint returns a page of projects and each project includes its owner name. The current implementation triggers one owner query per project and sometimes serializes lazy entities after the transaction has closed.', ['persistence','services'], [
        ('shape', 'What is a safe response boundary for this endpoint?', [('Load the required fields in a deliberate query and map them to a response DTO inside the service boundary', True), ('Serialize every managed entity and all lazy relations from the controller', False), ('Mark every relation EAGER so all future reads fetch everything', False)]),
        ('fetch', 'How should the repeated owner lookups be addressed?', [('Fetch the needed relation for this use case with a targeted projection, entity graph, or fetch join, and verify query counts', True), ('Add a database query inside the JSON serializer', False), ('Increase the page size until the extra queries disappear', False)]),
        ('page', 'What should remain true when changing the fetch plan?', [('Preserve pagination semantics and check for duplicate root rows from collection joins', True), ('Remove ordering so the database can pick any page', False), ('Load the entire table and paginate in memory', False)]),
    ]),
]

def language_files():
    for language in ('python', 'javascript', 'java'):
        for task in TASKS:
            competencies = task['competencies']
            tests = []
            for i, (inp, expected) in enumerate(zip(task['inputs'], task['expected'])):
                tests.append({'label': ['Representative input', 'Short input', 'Boundary and sign handling', 'Repeated values', 'Scale or integer boundary'][i], 'input': inp, 'expected': expected, 'visibility': 'sample' if i == 0 else 'hidden', 'competencies': competencies})
            content = {'slug': f'{language}-{task["slug"]}', 'skill': language, 'family': f'{language}.{task["slug"]}.advanced', 'type': 'coding', 'title': task['title'], 'statement': task['statement'], 'competencies': competencies, 'language': language, 'starter': {'python': 'def solve(nums):\n    # Return the requested result.\n    return None\n', 'javascript': 'function solve(nums) {\n  // Return the requested result.\n  return null;\n}', 'java': 'class Solution {\n    public static Object solve(int[] nums) {\n        // Return the requested result.\n        return null;\n    }\n}'}[language], 'reference': task[language], 'hints': ['Identify the invariant that stays true as the input is scanned.', 'Work through empty, repeated, and boundary-valued inputs.', 'Choose a time and memory bound that fits the stated input size.'], 'tests': tests, 'level': 'advanced', 'minutes': 18}
            write(content)

SQL_BASE = "CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, email TEXT); CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, amount REAL);"
def sql_file(slug,title,statement,competencies,reference,sets,minutes=18):
    tests=[]
    labels=['Representative shop','NULL values and missing links','Repeated business events','Small or empty groups']
    for n,(extra,expected) in enumerate(sets):
        tests.append({'label':labels[n],'dataset':SQL_BASE+extra,'expected':expected,'visibility':'sample' if n==0 else 'hidden','competencies':competencies})
    content={'slug':'sql-'+slug,'skill':'sql','family':'sql.'+slug+'.advanced','type':'sql','title':title,'statement':statement,'competencies':competencies,'language':'sql','schema':SQL_BASE,'sample_rows':{'customers':[[1,'Ada','ada@example.com'],[2,'Lin',None]],'orders':[[1,1,20]]},'starter':'SELECT 1\n-- Build the requested result.\n','reference':reference,'hints':['Translate each output row into a precise group or relationship.','Test missing values, unmatched keys, and repeated events.','Make ordering explicit when the result contract requires it.'],'tests':tests,'level':'advanced','minutes':minutes}
    write(content)

def spring_scenarios():
    for slug,title,statement,competencies,questions in SCENARIOS:
        qrows=[];answers={}
        for ident,prompt,options in questions:
            rows=[]
            for n,item in enumerate(options):
                if isinstance(item,tuple):text,correct=item
                else:text,correct=item,n==0
                oid=f'{ident}-{n+1}';rows.append({'id':oid,'text':text})
                if correct:answers[ident]=oid
            qrows.append({'id':ident,'prompt':prompt,'options':rows})
        write({'slug':'spring-boot-'+slug,'skill':'spring-boot','family':'spring-boot.'+slug+'.advanced','type':'scenario','title':title,'statement':statement,'competencies':competencies,'questions':qrows,'answers':answers,'explanation_prompt':'In 2–4 sentences, explain the framework boundary behind your choices and one concrete way you would verify the behavior.','explanation_rubric':['Names the relevant Spring or application boundary accurately.','Connects the boundary to the failure or correctness behavior in this scenario.','Suggests a concrete verification step such as a focused integration test.'],'hints':['Name the framework boundary before choosing a fix.','Consider what happens on failure, not only on the success path.'],'level':'advanced','minutes':10})

def ensure_existing_spring_rubrics():
    prompt='In 2–4 sentences, explain the framework boundary behind your choices and one concrete way you would verify the behavior.'
    rubric=['Names the relevant Spring or application boundary accurately.','Connects the boundary to the failure or correctness behavior in this scenario.','Suggests a concrete verification step such as a focused integration test.']
    competencies={slug:comps for slug,_,_,comps,_ in SCENARIOS}
    for path in OUT.glob('spring-boot-*.yaml'):
        content=yaml.safe_load(path.read_text(encoding='utf-8'))
        if content.get('skill')!='spring-boot' or content.get('type')!='scenario':continue
        changed=False
        if content.get('slug','').removeprefix('spring-boot-') in competencies and content.get('competencies')!=competencies[content['slug'].removeprefix('spring-boot-')]:
            content['competencies']=competencies[content['slug'].removeprefix('spring-boot-')];changed=True
        if content.get('minutes')!=10:content['minutes']=10;changed=True
        if not content.get('explanation_rubric'):
            content['explanation_prompt']=prompt;content['explanation_rubric']=rubric;changed=True
        if not changed:continue
        path.write_text(yaml.safe_dump(content,allow_unicode=True,sort_keys=False,width=96),encoding='utf-8')
        print('updated Spring Boot assessment metadata in',path.name)

def write(content):
    path=OUT/(content['slug']+'.yaml')
    if path.exists():
        print('kept existing',path.name);return
    path.write_text(yaml.safe_dump(content,allow_unicode=True,sort_keys=False,width=96),encoding='utf-8')
    print('created',path.name)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    language_files()
    common=['aggregation','duplicates','null_handling','joins']
    sql_file('customer-rollup','Customer event rollup','Return one row per customer with id, count of matched orders, and total amount. Keep repeated order events, show customers with no matches, treat a NULL amount as zero in the total, ignore orders with no customer, and order by customer id.',common,'SELECT c.id,COUNT(o.id),COALESCE(SUM(o.amount),0) FROM customers c LEFT JOIN orders o ON o.customer_id=c.id GROUP BY c.id ORDER BY c.id',[
        ("INSERT INTO customers VALUES (1,'Ada','a'),(2,'Lin',NULL),(3,'Sam','s'); INSERT INTO orders VALUES (1,1,20),(2,1,20),(3,3,15);",[[1,2,40.0],[2,0,0],[3,1,15.0]]),
        ("INSERT INTO customers VALUES (1,'Ada','a'),(2,'Lin',NULL); INSERT INTO orders VALUES (1,1,NULL),(2,NULL,9);",[[1,1,0],[2,0,0]]),
        ("INSERT INTO customers VALUES (1,'Ada','a'); INSERT INTO orders VALUES (1,1,12),(2,1,12),(3,1,18);",[[1,3,42.0]]),
        ("INSERT INTO customers VALUES (5,'No orders',NULL);",[[5,0,0]]),
    ])
    sql_file('inclusive-filter','Inclusive order window','Return id and amount for orders with amount greater than or equal to 50. Exclude NULL amounts and order by id.', ['filtering','null_handling'], 'SELECT id,amount FROM orders WHERE amount>=50 AND amount IS NOT NULL ORDER BY id',[
        ("INSERT INTO customers VALUES (1,'A','a'); INSERT INTO orders VALUES (1,1,49),(2,1,50),(3,1,51);",[[2,50.0],[3,51.0]]),
        ("INSERT INTO customers VALUES (1,'A','a'); INSERT INTO orders VALUES (1,1,NULL),(2,NULL,50);",[[2,50.0]]),
        ("INSERT INTO customers VALUES (1,'A','a'); INSERT INTO orders VALUES (1,1,50),(2,1,50);",[[1,50.0],[2,50.0]]),
        ("INSERT INTO customers VALUES (1,'A','a'); INSERT INTO orders VALUES (1,1,49);",[]),
    ])
    sql_file('duplicate-customer-names','Repeated customer names','Return each non-NULL customer name that appears at least twice, with its row count, ordered by name. Repeated names are distinct customer records.', ['aggregation','duplicates','null_handling','filtering'], 'SELECT name,COUNT(*) FROM customers WHERE name IS NOT NULL GROUP BY name HAVING COUNT(*)>=2 ORDER BY name',[
        ("INSERT INTO customers VALUES (1,'Ada','a'),(2,'Ada','b'),(3,'Lin','l');",[['Ada',2]]),
        ("INSERT INTO customers VALUES (1,NULL,'a'),(2,NULL,'b'),(3,'Lin',NULL);",[]),
        ("INSERT INTO customers VALUES (1,'Sam','a'),(2,'Sam','b'),(3,'Sam','c');",[['Sam',3]]),
        ("INSERT INTO customers VALUES (1,'Only','a');",[]),
    ])
    sql_file('orphan-orders','Orders without a customer','Return order id and customer_id for orders whose customer_id is NULL or does not match a customer. Return each order once, ordered by order id.', ['joins','null_handling','duplicates','filtering'], 'SELECT o.id,o.customer_id FROM orders o WHERE o.customer_id IS NULL OR NOT EXISTS (SELECT 1 FROM customers c WHERE c.id=o.customer_id) ORDER BY o.id',[
        ("INSERT INTO customers VALUES (1,'Ada','a'); INSERT INTO orders VALUES (1,1,2),(2,9,3),(3,NULL,4);",[[2,9],[3,None]]),
        ("INSERT INTO customers VALUES (1,'Ada','a'); INSERT INTO orders VALUES (1,NULL,2),(2,1,3);",[[1,None]]),
        ("INSERT INTO customers VALUES (1,'Ada','a'),(2,'Lin','l'); INSERT INTO orders VALUES (1,8,2),(2,8,3);",[[1,8],[2,8]]),
        ("INSERT INTO customers VALUES (1,'Ada','a');",[]),
    ])
    spring_scenarios()
    ensure_existing_spring_rubrics()

if __name__=='__main__':main()
