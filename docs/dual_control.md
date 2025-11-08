# Dual-Control Runbook

Version: 0.1.0  
Owner: Ops Engineering (Codex CLI)  
Last Reviewed: 2025-11-07

## 1. Overview

The USDT Trading Assistant enforces dual approval for all sensitive user lifecycle changes and settlements. Every
approval requires:

1. **Primary approver** - initiates the approval action
2. **Secondary approver** - distinct operator who co-signs the change
3. **Reason** - business justification (>= 5 characters) stored in the audit log

Schema changes (migration `backend/migrations/0002_dual_control_secondary.cjs`) added:

- `approval_reason TEXT`
- `secondary_approver_id UUID`
- `secondary_approved_at TIMESTAMP`

## 2. Workflow

1. **Queue review**
   - `GET /api/dual-control/requests` -> pending approvals
   - Ops console (`frontend/`) shows the same list with requester context
2. **Select approvers**
   - Fetch from `GET /api/users/approved` (UI drop-downs use this endpoint)
   - Enforce primary != secondary
3. **Approve**
   - API call: `POST /api/users/:id/approve`

     ```json
     {
       "dualControlRequestId": "<request-id>",
       "approverId": "<primary-uuid>",
       "secondaryApproverId": "<secondary-uuid>",
       "reason": "Business justification"
     }
     ```

   - Fastify/Zod returns HTTP 400 if `reason` missing/short or approvers duplicated. Reproduce via:

     ```bash
     cd backend
     npx tsx scripts/check-approval-reason.ts
     ```

4. **Reject**
   - Endpoint: `POST /api/users/:id/reject`

     ```json
     {
       "dualControlRequestId": "<request-id>",
       "approverId": "<primary-uuid>",
       "reason": "Why request was denied"
     }
     ```

5. **Audit / Evidence**
   - `audit_logs` captures `dual_control_approved/dual_control_rejected` with both approvers & reason
   - `dual_control_requests` retains the secondary approver and timestamps

## 3. UI Guidance

- **Primary/Secondary selectors**: autopopulated from approved users; UI prevents selecting the same operator twice
- **Reason textarea**: placeholder explains acceptable justifications; inline errors highlight missing/short input
- **Reject form**: single approver + reason; mirrors backend requirement
- **Refresh button**: fetches queue + approvers to maintain parity with backend state

## 4. Manual Tests

1. `npm run migrate:dev` (ensures schema up to date)
2. `npm test` (backend) - `User domain > ensures approval reason and distinct secondary approver`
3. `npx tsx scripts/manual-smoke.ts` - seeds approvers, creates pending user, approves via dual-control path
4. `psql ... SELECT approval_reason, secondary_approver_id IS NOT NULL ...;` - confirms DB integrity
5. `npx tsx scripts/check-approval-reason.ts` - expected output:

   ```json
   {
     "statusCode": 400,
     "body": "{\"message\":\"Validation failed\", ... }"
   }
   ```
