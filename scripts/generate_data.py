"""Curated synthetic Slack fixture; no expected scores or classification labels in data."""
from pathlib import Path
import json
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]
# channel, author, role, phase, text. Literal facts are intentionally reviewable.
ROWS = [
('atlas-testing','David','ME','Prototype','Risk: Vibration on motor mount MM-2100 measured 4.2 mm/s on bench A at 2000 RPM, loaded. Fixture unchanged; independent log attached, pending reconciliation.'),
('atlas-testing','Mei','ME','Prototype','Risk: Vibration on motor mount MM-2100 measured 6.8 mm/s on bench A at 2000 RPM, loaded. Fixture unchanged; independent log attached, pending reconciliation.'),
('atlas-mechanical','Alex','ME','Prototype','Risk: Vibration on motor mount MM-2100 measured 6.8 mm/s on bench A at 3000 RPM, loaded. Fixture unchanged; independent log attached, pending reconciliation.'),
('atlas-mechanical','Mei','ME','Prototype','Forwarded: Risk: Vibration on motor mount MM-2100 measured 6.8 mm/s on bench A at 2000 RPM, loaded. Fixture unchanged; independent log attached, pending reconciliation.'),
('atlas-supply-chain','Raj Patel','SC','Prototype','Risk: Lead time for supplier driver chip MD-4820-X is 12 weeks. BOM allocation is not secured; purchasing needs the delivery estimate before releasing the order.'),
('atlas-supply-chain','Raj Patel','SC','Prototype','Update replaces M005: Risk: Lead time for supplier driver chip MD-4820-X is 20 weeks. BOM allocation is not secured; purchasing needs the delivery estimate before releasing the order.'),
('atlas-electrical','Priya Nair','EE','Prototype','Forwarded: Risk: Lead time for supplier driver chip MD-4820-X is 20 weeks. BOM allocation is not secured; purchasing needs the delivery estimate before releasing the order.'),
('atlas-electrical','Priya Nair','EE','Prototype','Dependency handoff: alternate motor driver footprint review completed. EE will check the interface before SC requests a second vendor quotation.'),
('atlas-testing','Priya Nair','EE','Prototype','Risk: Thermal result for battery BP-2400 rev B at 24V is 61 C on bench B, loaded. Cooling fixture recorded; pack release awaits an engineering review.'),
('atlas-electrical','Jun','EE','Prototype','Risk: Thermal result for battery BP-2400 rev C at 48V is 74 C on bench B, loaded. Cooling fixture recorded; pack release awaits an engineering review.'),
('atlas-mechanical','Sarah Chen','ME','Prototype','Integration update: battery cooling duct fit check completed on chassis. Bracket access is clear; thermal team can instrument the next pack build.'),
('atlas-electrical','Priya Nair','EE','Validation','Risk: Battery power board PB-4800 output voltage is 24V with firmware v2.1 on bench C. The harness team needs a confirmed interface requirement before release.'),
('atlas-testing','Jun','EE','Validation','Risk: Battery power board PB-4800 output voltage is 48V with firmware v2.1 on bench C. The harness team needs a confirmed interface requirement before release.'),
('atlas-leadership','Marcus Lee','EM','Prototype','Risk: Milestone validation schedule date is 10/15. Schedule reserve depends on reliability sign-off; leadership has not approved customer communication.'),
('atlas-leadership','Marcus Lee','EM','Prototype','Update replaces M014: Risk: Milestone validation schedule date is 10/29. Schedule reserve depends on reliability sign-off; leadership has not approved customer communication.'),
('atlas-leadership','Lena Torres','PM','Design','Scope decision approved: customer pilot excludes autonomous trailer loading. Roadmap retains supervised docking; commercial impact needs a private account review.'),
('atlas-general','Marcus Lee','EM','Prototype','Milestone update: public integration checkpoint remains 10/01. No customer date committed; testing sign-off is still required.'),
('atlas-general','Marcus Lee','EM','Prototype','Dependency update: calibration handoff ready for controls review. Schedule owner needs one acceptance checklist rather than separate team sign-offs.'),
('atlas-mechanical','Sarah Chen','ME','Prototype','Risk: Integration of chassis service panel needs a fit check. Harness access is obstructed; mechanical owner must validate the assembly sequence.'),
('atlas-mechanical','David','ME','Production','Tolerance update: chassis supplier drawing inspection ready. DFM review confirmed the production fixture reference; testing team will audit the first lot.'),
('atlas-electrical','Priya Nair','EE','Design','Design decision: connector selection favors keyed power board plugs. Architecture review approved a replaceable harness interface with service access.'),
('atlas-mechanical','Alex','ME','Design','Design decision: motor enclosure CAD review completed. Mechanical architecture keeps the split housing for bearing inspection.'),
('atlas-general','Lena Torres','PM','Design','Scope decision: requirements for customer docking recovery approved. Roadmap keeps operator confirmation while product measures intervention frequency.'),
('atlas-testing','Mei','ME','Prototype','Testing update: motor mount calibration rig ready. Integration checks completed before vibration acquisition; fixture photos uploaded for review.'),
('atlas-mechanical','Sarah Chen','ME','Production','Integration update: chassis manufacturing fixture ready. Quality inspection yield is 92%; production fit check uses the released locating pins.'),
('atlas-supply-chain','Raj Patel','SC','Production','Supplier update: chassis production contract confirmed. Quality inspection plan completed; BOM purchasing can release the fixture order.'),
('atlas-testing','Mei','ME','Validation','Testing update: reliability soak completed on chassis. Quality inspection found no fastener migration; integration checklist awaits owner approval.'),
('atlas-electrical','Jun','EE','Prototype','Firmware update: interface error code E204 reproduced with motor driver v2.1. Battery power sequencing trace attached; patch testing starts after review.'),
('atlas-electrical','Priya Nair','EE','Production','Battery update: supplier pack inspection completed. Quality yield is 98%; production voltage audit retained the 24V harness acceptance limit.'),
('atlas-supply-chain','Raj Patel','SC','Production','Lead time update: supplier connector CN-3100 shipment confirmed Friday. Quality receipt inspection remains required before BOM release.'),
('atlas-general','Marcus Lee','EM','Production','Milestone update: manufacturing quality gate ready for schedule review. Supplier audit confirmed the next release checklist owner.'),
('atlas-general','Lena Torres','PM','Production','Milestone decision: customer quality acceptance review approved for the production pilot. Scope review keeps dock recovery in the launch checklist.'),
('atlas-supply-chain','Raj Patel','SC','Prototype','Supplier decision: vendor contract for harness HV-2400 approved. Procurement retains a second source; lead time confirmation due Oct 29.'),
('atlas-mechanical','David','ME','Design','Tolerance review: CAD stack-up for chassis service hatch ready. Design decision pending manufacturing feedback, not a build blocker.'),
('atlas-testing','Mei','ME','Validation','Quality update: inspection repeatability completed on bench D. Testing log records 96% agreement across independent gauge operators.'),
('atlas-electrical','Jun','EE','Validation','Thermal update: cooling fan characterization completed on bench D. Testing result recorded 39 C at 3.5A; battery team will assess airflow margin.'),
('atlas-general','Marcus Lee','EM','Validation','Dependency decision: reliability handoff owner approved. Milestone schedule review will accept the test report only after quality signs the traceability sheet.'),
('atlas-general','Lena Torres','PM','Validation','Scope update: customer acceptance notes ready. Testing review separates usability complaints from mechanical reliability evidence.'),
('atlas-mechanical','Alex','ME','Prototype','Motor update: replacement bearing assembly ready for integration. Testing instructions specify bench D, unloaded, at 2000 RPM.'),
('atlas-testing','David','ME','Prototype','Vibration update: sensor calibration completed on bench D at 2000 RPM. Testing log measured 0.4 mm/s on the reference shaker, not on the motor mount.'),
('atlas-supply-chain','Raj Patel','SC','Production','Quality update: supplier packaging inspection completed. Procurement found 3% cosmetic rejects; BOM remains usable after sorting.'),
('atlas-general','Marcus Lee','EM','Design','Milestone review: architecture requirements checklist ready. Schedule estimates remain provisional until component selection finishes.'),
('atlas-electrical','Priya Nair','EE','Design','Battery design decision: power board fuse access approved. Thermal requirements remain open until the pack enclosure geometry is frozen.'),
('atlas-mechanical','Sarah Chen','ME','Prototype','Integration update: chassis cable-routing jig ready. Testing crew confirmed service-panel removal does not disturb harness retention.'),
('atlas-general','Lena Torres','PM','Prototype','Scope update: customer demo script ready. Milestone review keeps docking and manual recovery; no production promise in the prototype presentation.'),
('atlas-supply-chain','Raj Patel','SC','Prototype','Delivery confirmed: replacement motors arrive Friday. Receiving will record serials before mechanical integration starts.'),
('atlas-general','Alex','ME','Prototype','Forwarded: Delivery confirmed: replacement motors arrive Friday. Receiving will record serials before mechanical integration starts.'),
('atlas-electrical','Jun','EE','Prototype','Firmware interface update: boot-sequence trace completed on power board. Testing needs one regression run with v2.2 before closing E204.'),
('atlas-testing','Mei','ME','Prototype','Testing update: integration harness continuity checks completed. Chassis fit check cleared the prototype build checklist.'),
('atlas-supply-chain','Raj Patel','SC','Production','Procurement update: vendor quality certificate ready for enclosure fasteners. BOM contract review confirmed the incoming-inspection owner.'),
('atlas-mechanical','David','ME','Production','Tolerance decision: supplier fixture datum approved. Quality inspection uses the chassis reference pin before production release.'),
('atlas-general','Marcus Lee','EM','Production','Dependency update: manufacturing handoff checklist completed. Quality and supplier owners must acknowledge their remaining release tasks.'),
('atlas-leadership','Lena Torres','PM','Production','Scope risk: customer contract exposes a late-delivery penalty. Roadmap owner needs a private commercial review before changing the pilot commitment.'),
('atlas-electrical','Priya Nair','EE','Validation','Firmware interface decision: error code E204 recovery approved in v2.2. Testing regression report retains a manual reset case.'),
('atlas-testing','Jun','EE','Validation','Thermal testing update: cooling duct instrument harness ready. Battery pack soak can start after temperature probe calibration.'),
('atlas-supply-chain','Raj Patel','SC','Design','Supplier component selection decision: vendor requested a BOM forecast. Design decision remains open while procurement compares connector families.'),
('atlas-mechanical','Sarah Chen','ME','Design','Design decision: chassis architecture review completed. CAD packaging confirms access to battery service points.'),
('atlas-general','Marcus Lee','EM','Prototype','Dependency update: build-room tool checkout completed. Integration team owns the fixture return checklist.'),
('atlas-testing','David','ME','Prototype','Testing notes: integration rig operators confirmed the bench D procedure. Chassis assembly must be photographed before the overnight run.'),
('atlas-general','Lena Torres','PM','Design','Scope notes: customer interview transcript ready. Requirements review should distinguish warehouse aisle width from docking workflow.'),
]
NOISE = ['Lunch poll: noodles or sandwiches?', 'Coffee is ready in the kitchen.', 'Thanks for helping with the demo cleanup!', 'Happy birthday Jun!', 'Anyone for a walk after lunch?', 'Great job on the team presentation.', 'Emoji reaction thread for the new stickers.', 'Office printer has fresh paper.', 'Weekend cycling photos in the social thread.', 'Pizza order closes at noon.', 'Thanks Sarah for finding my notebook.', 'Coffee beans arrived; please label your mugs.']


def generate():
    result = []
    for i, (channel, author, role, phase, text) in enumerate(ROWS, 1):
        # Most useful content is within the approved 72h window. Last three business
        # messages intentionally document historical context outside the window.
        clock = datetime(2026, 9, 27, 8, tzinfo=timezone.utc) + timedelta(minutes=8*i)
        if i in (34, 41, 56):
            clock = datetime(2026, 9, 25, 12, tzinfo=timezone.utc) + timedelta(minutes=i)
        if i >= 58:
            clock = datetime(2026, 9, 21, 10, tzinfo=timezone.utc) + timedelta(hours=i-58)
        row = dict(message_id=f'M{i:03}',channel=channel,timestamp=clock.isoformat().replace('+00:00','Z'),author=author,author_role=role,thread_id=f'T{i:03}',text=text,project='Atlas',phase=phase,parent_id=None,reactions=i%5)
        # One real reply thread; attention will be recomputed after authorization.
        if i == 49:
            row['thread_id'] = 'T044'; row['parent_id'] = 'M044'
        result.append(row)
    for i, text in enumerate(NOISE, len(ROWS)+1):
        result.append(dict(message_id=f'M{i:03}',channel='atlas-general',timestamp='2026-09-27T16:00:00Z',author='Alex',author_role='ME',thread_id=f'T{i:03}',text=text,project='Atlas',phase='Prototype',parent_id=None,reactions=3))
    assert len(result) == 72
    return result


if __name__ == '__main__':
    (ROOT/'data/slack_messages.json').write_text(json.dumps(generate(),indent=2)+'\n')
    print('Generated 72 curated synthetic messages; human review pending')
