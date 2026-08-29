# Sample Session

## Low Risk
```bash
python main.py demo low-risk
```
Expected: `executed`

## Approval-Gated Email
```bash
python main.py demo approval
```
Expected: `approval_required` followed by `Email send simulated.`

## Tampering
```bash
python main.py demo tamper
```
Expected: `Action changed after approval.`

## Forbidden Tool
```bash
python main.py demo forbidden
```
Expected: `Action is explicitly forbidden.`

## Prompt Injection
```bash
python main.py demo injection
```
Expected: `Prompt-injection-like instructions were detected.`

## Unauthorized Role
```bash
python main.py demo unauthorized
```
Expected: `Role viewer lacks permission email.send.`
