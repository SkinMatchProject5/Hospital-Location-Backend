#!/usr/bin/env python3
"""새로운 XML 형식 테스트"""

from app.services.xml_parser import DiagnosisXMLParser

def test_new_xml_format():
    """새로운 XML 형식 테스트"""
    new_xml = """<root>
    <diagnosis>피부섬유종</diagnosis>
    <description>이미지에서는 작고 단단한 결절이 관찰되며, 중심부에 오목함(딤플 사인)이 있는 특징을 보입니다. 이 병변은 외상 후 섬유조직의 반응성 증식으로 발생하며, 대개 무통성입니다. 팔, 다리, 어깨 등에서 흔히 발생하며, 치료는 필요하지 않지만 원할 경우 절제가 가능합니다.</description>
</root>"""

    try:
        parser = DiagnosisXMLParser()
        result = parser.parse_xml(new_xml)
        
        print("✅ 새로운 XML 형식 파싱 성공!")
        print(f"   진단명: {result.diagnosis}")
        print(f"   신뢰도: {result.confidence_score}")
        print(f"   설명: {result.summary}")
        print(f"   유사질병 수: {len(result.similar_diseases)}")
        
        return True
    except Exception as e:
        print(f"❌ 새로운 XML 형식 파싱 실패: {e}")
        return False

def test_old_xml_format():
    """기존 XML 형식 테스트"""
    old_xml = """<root>
        <label id_code="0" score="85.0">광선각화증</label>
        <summary>자외선 노출이 많은 부위인 얼굴에 붉은색의 각질성 반점이 관찰됩니다.</summary>
        <similar_labels>
            <similar_label id_code="3" score="16.6">보웬병</similar_label>
        </similar_labels>
    </root>"""

    try:
        parser = DiagnosisXMLParser()
        result = parser.parse_xml(old_xml)
        
        print("✅ 기존 XML 형식 파싱 성공!")
        print(f"   진단명: {result.diagnosis}")
        print(f"   신뢰도: {result.confidence_score}")
        print(f"   설명: {result.summary}")
        print(f"   유사질병 수: {len(result.similar_diseases)}")
        
        return True
    except Exception as e:
        print(f"❌ 기존 XML 형식 파싱 실패: {e}")
        return False

if __name__ == "__main__":
    print("🔍 XML 파서 테스트")
    print("="*50)
    
    print("\n1️⃣ 새로운 XML 형식 테스트:")
    new_ok = test_new_xml_format()
    
    print("\n2️⃣ 기존 XML 형식 테스트:")
    old_ok = test_old_xml_format()
    
    if new_ok and old_ok:
        print("\n🎉 모든 XML 형식 지원 완료!")
    else:
        print("\n💥 일부 XML 형식에 문제가 있습니다.")
