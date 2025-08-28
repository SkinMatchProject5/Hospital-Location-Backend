"""Parser for fine-tuned model XML-like output.

Expected format example:

<root>
  <label id_code="1" score="60.0">기저세포암</label>
  <summary> ... </summary>
  <similar_labels>
    <similar_label id_code="3" score="12.0">보웬병</similar_label>
    <similar_label id_code="0" score="10.0">광선각화증</similar_label>
  </similar_labels>
</root>

Returns a dict compatible with the pipeline input contract:
{
  "diagnosis": str,
  "description": str | None,
  "similar_diseases": list[str],
  "region": None,
  "confidence": float | None  # 0..1
}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET


def _get_text(elem: Optional[ET.Element]) -> Optional[str]:
    if elem is None:
        return None
    text = elem.text or ""
    return text.strip() or None


def parse_ft_xml_to_model_output(xml_str: str) -> Dict[str, Any]:
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 XML 파싱 입력: {xml_str}")
    try:
        root = ET.fromstring(xml_str)
        logger.info(f"🔍 XML 루트 태그: {root.tag}")
        logger.info(f"🔍 XML 자식 요소들: {[child.tag for child in root]}")
        logger.info(f"🔍 XML 전체 구조: {ET.tostring(root, encoding='unicode')}")
    except Exception as e:
        logger.error(f"❌ XML 파싱 실패: {e}")
        # Fallback: return minimal dict
        return {
            "diagnosis": "",
            "description": None,
            "similar_diseases": [],
            "region": None,
            "confidence": None,
        }

    # Support both old and new XML formats
    diagnosis_elem = root.find("diagnosis") or root.find("label")
    logger.info(f"🔍 진단 요소 찾기: diagnosis_elem={diagnosis_elem}")
    
    # Direct access fallback if find() fails
    if diagnosis_elem is None:
        for child in root:
            logger.info(f"🔍 자식 요소: tag='{child.tag}', text='{child.text}'")
            if child.tag == "diagnosis":
                diagnosis_elem = child
                logger.info(f"🔍 직접 접근으로 찾음: {diagnosis_elem}")
                break
    
    if diagnosis_elem is not None:
        logger.info(f"🔍 진단 요소 텍스트: text='{diagnosis_elem.text}', tag='{diagnosis_elem.tag}'")
    diagnosis = _get_text(diagnosis_elem) or ""
    logger.info(f"🔍 최종 진단명: '{diagnosis}'")

    # Score normalization (0..100 -> 0..1) - only for old format
    conf = None
    if diagnosis_elem is not None:
        score_attr = diagnosis_elem.attrib.get("score")
        if score_attr is not None:
            try:
                conf = float(score_attr) / 100.0
            except ValueError:
                conf = None

    # Support both description and summary tags
    description_elem = root.find("description") or root.find("summary")
    description = _get_text(description_elem)

    similar: List[str] = []
    
    # New format: <similar_diseases>disease1, disease2</similar_diseases>
    similar_diseases_elem = root.find("similar_diseases")
    if similar_diseases_elem is not None:
        similar_text = _get_text(similar_diseases_elem)
        if similar_text:
            similar = [s.strip() for s in similar_text.split(',') if s.strip()]
    
    # Old format: <similar_labels><similar_label>...</similar_label></similar_labels>
    if not similar:
        sim_parent = root.find("similar_labels")
        if sim_parent is not None:
            for s in sim_parent.findall("similar_label"):
                name = _get_text(s)
                if name:
                    similar.append(name)

    result = {
        "diagnosis": diagnosis,
        "description": description,
        "similar_diseases": similar,
        "region": None,
        "confidence": conf,
    }
    logger.info(f"✅ XML 파싱 결과: {result}")
    return result

