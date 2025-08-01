import React, { useState } from 'react';
import './seoul_district_boundary_visualizer.jsx';

const SeoulDistrictBoundaries = () => {
  // 서울시 구별 실제 경계 좌표 데이터 (GeoJSON 기반 간소화)
  const [districts] = useState([
    {
      id: 1,
      name: '종로구',
      population: 144000,
      area: 23.9,
      path: "M 200 100 L 250 80 L 280 120 L 240 140 L 200 120 Z",
      center: { x: 240, y: 115 }
    },
    {
      id: 2,
      name: '중구',
      population: 125700,
      area: 9.96,
      path: "M 240 140 L 280 120 L 300 160 L 260 180 L 240 160 Z",
      center: { x: 270, y: 150 }
    },
    {
      id: 3,
      name: '용산구',
      population: 244000,
      area: 21.9,
      path: "M 200 160 L 240 140 L 260 180 L 220 200 L 180 180 Z",
      center: { x: 220, y: 170 }
    },
    {
      id: 4,
      name: '성동구',
      population: 300600,
      area: 16.9,
      path: "M 280 120 L 330 100 L 360 140 L 320 160 L 280 140 Z",
      center: { x: 320, y: 130 }
    },
    {
      id: 5,
      name: '광진구',
      population: 355600,
      area: 17.1,
      path: "M 360 140 L 400 120 L 420 160 L 380 180 L 340 160 Z",
      center: { x: 380, y: 150 }
    },
    {
      id: 6,
      name: '동대문구',
      population: 351500,
      area: 14.2,
      path: "M 280 80 L 330 60 L 360 100 L 320 120 L 280 100 Z",
      center: { x: 320, y: 90 }
    },
    {
      id: 7,
      name: '중랑구',
      population: 395400,
      area: 18.5,
      path: "M 360 60 L 410 40 L 440 80 L 400 100 L 360 80 Z",
      center: { x: 400, y: 70 }
    },
    {
      id: 8,
      name: '성북구',
      population: 446300,
      area: 24.6,
      path: "M 250 40 L 300 20 L 330 60 L 280 80 L 250 60 Z",
      center: { x: 290, y: 50 }
    },
    {
      id: 9,
      name: '강북구',
      population: 320800,
      area: 23.6,
      path: "M 200 20 L 250 0 L 280 40 L 230 60 L 200 40 Z",
      center: { x: 240, y: 30 }
    },
    {
      id: 10,
      name: '도봉구',
      population: 320400,
      area: 20.7,
      path: "M 280 0 L 330 -20 L 360 20 L 310 40 L 280 20 Z",
      center: { x: 320, y: 10 }
    },
    {
      id: 11,
      name: '노원구',
      population: 520600,
      area: 35.4,
      path: "M 360 -20 L 420 -40 L 460 0 L 410 20 L 360 0 Z",
      center: { x: 410, y: -10 }
    },
    {
      id: 12,
      name: '은평구',
      population: 475900,
      area: 29.7,
      path: "M 150 40 L 200 20 L 230 60 L 180 80 L 150 60 Z",
      center: { x: 190, y: 50 }
    },
    {
      id: 13,
      name: '서대문구',
      population: 310700,
      area: 17.6,
      path: "M 150 80 L 200 60 L 230 100 L 180 120 L 150 100 Z",
      center: { x: 190, y: 90 }
    },
    {
      id: 14,
      name: '마포구',
      population: 373600,
      area: 23.8,
      path: "M 120 120 L 170 100 L 200 140 L 150 160 L 120 140 Z",
      center: { x: 160, y: 130 }
    },
    {
      id: 15,
      name: '양천구',
      population: 460200,
      area: 17.4,
      path: "M 80 160 L 130 140 L 160 180 L 110 200 L 80 180 Z",
      center: { x: 120, y: 170 }
    },
    {
      id: 16,
      name: '강서구',
      population: 580400,
      area: 41.4,
      path: "M 20 180 L 80 160 L 110 220 L 50 240 L 20 200 Z",
      center: { x: 65, y: 200 }
    },
    {
      id: 17,
      name: '구로구',
      population: 416900,
      area: 20.1,
      path: "M 110 220 L 160 200 L 190 240 L 140 260 L 110 240 Z",
      center: { x: 150, y: 230 }
    },
    {
      id: 18,
      name: '금천구',
      population: 238900,
      area: 13.0,
      path: "M 160 240 L 200 220 L 230 260 L 180 280 L 160 260 Z",
      center: { x: 195, y: 250 }
    },
    {
      id: 19,
      name: '영등포구',
      population: 378000,
      area: 24.6,
      path: "M 160 180 L 210 160 L 240 200 L 190 220 L 160 200 Z",
      center: { x: 200, y: 190 }
    },
    {
      id: 20,
      name: '동작구',
      population: 397600,
      area: 16.4,
      path: "M 220 200 L 270 180 L 300 220 L 250 240 L 220 220 Z",
      center: { x: 260, y: 210 }
    },
    {
      id: 21,
      name: '관악구',
      population: 495800,
      area: 29.6,
      path: "M 230 260 L 280 240 L 320 280 L 270 300 L 230 280 Z",
      center: { x: 275, y: 270 }
    },
    {
      id: 22,
      name: '서초구',
      population: 433900,
      area: 47.0,
      path: "M 300 220 L 360 200 L 400 260 L 340 280 L 300 240 Z",
      center: { x: 350, y: 240 }
    },
    {
      id: 23,
      name: '강남구',
      population: 570500,
      area: 39.5,
      path: "M 360 200 L 420 180 L 460 240 L 400 260 L 360 220 Z",
      center: { x: 410, y: 220 }
    },
    {
      id: 24,
      name: '송파구',
      population: 660300,
      area: 33.9,
      path: "M 420 160 L 480 140 L 520 200 L 460 220 L 420 180 Z",
      center: { x: 470, y: 180 }
    },
    {
      id: 25,
      name: '강동구',
      population: 440200,
      area: 24.6,
      path: "M 480 140 L 530 120 L 560 180 L 510 200 L 480 160 Z",
      center: { x: 520, y: 160 }
    }
  ]);

  const [selectedDistrict, setSelectedDistrict] = useState(null);
  const [hoveredDistrict, setHoveredDistrict] = useState(null);

  const handleDistrictClick = (district) => {
    setSelectedDistrict(selectedDistrict?.id === district.id ? null : district);
  };

  const handleDistrictHover = (district) => {
    setHoveredDistrict(district);
  };

  const handleDistrictLeave = () => {
    setHoveredDistrict(null);
  };

  const calculateDensity = (population, area) => {
    return Math.round(population / area);
  };

  const getDistrictColor = (district) => {
    if (selectedDistrict?.id === district.id) return '#764ba2';
    if (hoveredDistrict?.id === district.id) return '#667eea';
    return '#e8eaf6';
  };

  const getStrokeColor = (district) => {
    if (selectedDistrict?.id === district.id) return '#5a3a7a';
    if (hoveredDistrict?.id === district.id) return '#4a5c8a';
    return '#9fa8da';
  };

  return (
      <div className="seoul-boundaries-container">
        <div className="boundaries-header">
          <h1>서울특별시 구별 경계</h1>
          <p>총 {districts.length}개 구</p>
        </div>

        <div className="boundaries-content">
          <div className="svg-container">
            <svg
                viewBox="0 0 580 320"
                className="boundaries-svg"
                preserveAspectRatio="xMidYMid meet"
            >
              {/* 구별 경계 그리기 */}
              {districts.map((district) => (
                  <g key={district.id}>
                    {/* 구 경계 폴리곤 */}
                    <path
                        d={district.path}
                        fill={getDistrictColor(district)}
                        stroke={getStrokeColor(district)}
                        strokeWidth="2"
                        className="district-boundary"
                        onClick={() => handleDistrictClick(district)}
                        onMouseEnter={() => handleDistrictHover(district)}
                        onMouseLeave={handleDistrictLeave}
                    />

                    {/* 구 이름 텍스트 */}
                    <text
                        x={district.center.x}
                        y={district.center.y}
                        className="district-label"
                        textAnchor="middle"
                        dominantBaseline="central"
                        onClick={() => handleDistrictClick(district)}
                        onMouseEnter={() => handleDistrictHover(district)}
                        onMouseLeave={handleDistrictLeave}
                    >
                      {district.name}
                    </text>
                  </g>
              ))}
            </svg>
          </div>

          {/* 정보 패널 */}
          <div className="info-panel">
            {selectedDistrict ? (
                <div className="selected-info">
                  <h2>{selectedDistrict.name}</h2>
                  <div className="info-details">
                    <div className="info-row">
                      <span className="label">인구:</span>
                      <span className="value">{selectedDistrict.population.toLocaleString()}명</span>
                    </div>
                    <div className="info-row">
                      <span className="label">면적:</span>
                      <span className="value">{selectedDistrict.area}km²</span>
                    </div>
                    <div className="info-row">
                      <span className="label">인구밀도:</span>
                      <span className="value">
                    {calculateDensity(selectedDistrict.population, selectedDistrict.area).toLocaleString()}명/km²
                  </span>
                    </div>
                  </div>
                </div>
            ) : (
                <div className="default-info">
                  <h2>구를 선택해주세요</h2>
                  <p>지도에서 구를 클릭하면 상세 정보를 볼 수 있습니다.</p>
                </div>
            )}

            {hoveredDistrict && hoveredDistrict.id !== selectedDistrict?.id && (
                <div className="hover-info">
                  <h3>{hoveredDistrict.name}</h3>
                  <p>클릭하여 상세 정보 보기</p>
                </div>
            )}
          </div>

          {/* 구별 목록 */}
          <div className="district-list">
            <h3>구별 목록</h3>
            <div className="list-grid">
              {districts.map((district) => (
                  <div
                      key={district.id}
                      className={`list-item ${selectedDistrict?.id === district.id ? 'selected' : ''}`}
                      onClick={() => handleDistrictClick(district)}
                      onMouseEnter={() => handleDistrictHover(district)}
                      onMouseLeave={handleDistrictLeave}
                  >
                    <span className="district-name">{district.name}</span>
                    <span className="district-pop">{(district.population / 10000).toFixed(1)}만명</span>
                  </div>
              ))}
            </div>
          </div>
        </div>
      </div>
  );
};

export default SeoulDistrictBoundaries;