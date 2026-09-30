import pytest
from src.identifiers import extract_identifiers

@pytest.mark.parametrize('text,kind,value,unit',[
    ('24V','voltage','24','V'),('48 V','voltage','48','V'),('3.5A','current','3.5','A'),('350 mA','current','350','mA'),
    ('2000 RPM','speed','2000','RPM'),('3000 RPM','speed','3000','RPM'),('4.2 mm/s','vibration','4.2','mm/s'),
    ('6.8 mm/s','vibration','6.8','mm/s'),('12 weeks','lead_time','12','weeks'),('20 wks','lead_time','20','weeks'),
    ('3 days','lead_time','3','days'),('rev B','revision','REV B',''),('rev C','revision','REV C',''),
    ('v2.1','version','V2.1',''),('MD-4820-X','part','MD-4820-X',''),('10/15','date','10/15',''),
    ('Oct 29','date','OCT 29',''),('Friday','date','FRIDAY',''),('2026-09-27','date','2026-09-27',''),
    ('E204','error','E204',''),('61 C','temperature','61','C'),('-5 °C','temperature','-5','C'),('98%','percentage','98','%'),
    ('60 Hz','vibration','60','Hz'),('1.2g','vibration','1.2','g')])
def test_typed_span_provenance(text,kind,value,unit):
    found=extract_identifiers('prefix '+text+' suffix','MTEST')
    e=next(e for e in found if e.kind==kind)
    assert (e.value,e.unit,e.raw,e.source_message_id)==(value,unit,text,'MTEST')
    assert ('prefix '+text+' suffix')[e.start:e.end]==e.raw

@pytest.mark.parametrize('text',['X24Vfoo','motorE204foo','revolution B','identifier 1234'])
def test_boundaries(text):
    assert not extract_identifiers(text,'X')

@pytest.mark.parametrize('left,right',[('24V','48V'),('rev B','rev C'),('12 weeks','20 weeks'),('2000 RPM','3000 RPM'),('v2.1','v2.2')])
def test_distinctions_not_normalized_away(left,right):
    assert extract_identifiers(left,'A')[0].key != extract_identifiers(right,'B')[0].key
