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
    try:
        root = ET.fromstring(xml_str)
    except Exception:
        # Fallback: return minimal dict
        return {
            "diagnosis": "",
            "description": None,
            "similar_diseases": [],
            "region": None,
            "confidence": None,
        }

    label = root.find("label")
    diagnosis = _get_text(label) or ""

    # Score normalization (0..100 -> 0..1)
    conf = None
    if label is not None:
        score_attr = label.attrib.get("score")
        if score_attr is not None:
            try:
                conf = float(score_attr) / 100.0
            except ValueError:
                conf = None

    description = _get_text(root.find("summary"))

    similar: List[str] = []
    sim_parent = root.find("similar_labels")
    if sim_parent is not None:
        for s in sim_parent.findall("similar_label"):
            name = _get_text(s)
            if name:
                similar.append(name)

    return {
        "diagnosis": diagnosis,
        "description": description,
        "similar_diseases": similar,
        "region": None,
        "confidence": conf,
    }

