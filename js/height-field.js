// Volume-preserving, closed height field. Cell means stay physical ledger values.
export function heightField(cells, nx = 8, ny = 8, dx = 0.5, dy = 0.5) {
  if (cells.length !== nx * ny || !cells.every(Number.isFinite) || cells.some(h => h < 0) || !(dx > 0 && dy > 0)) throw new Error("Invalid height field");
  const positions = [], cellVolumes = [], inset = 0.04;
  const height = (i, j) => cells[i * ny + j];
  const corner = (i, j) => {
    const adjacent = [];
    for (const x of [i - 1, i]) for (const y of [j - 1, j]) if (x >= 0 && y >= 0 && x < nx && y < ny) adjacent.push(height(x, y));
    return Math.min(...adjacent);
  };
  const emit = (a, b, c) => positions.push(...a, ...b, ...c);
  for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) {
    const h = height(i, j), outer = [[i, j], [i + 1, j], [i + 1, j + 1], [i, j + 1]].map(([x, y]) => [x * dx, corner(x, y), -y * dy]);
    const inner = [[i + inset, j + inset], [i + 1 - inset, j + inset], [i + 1 - inset, j + 1 - inset], [i + inset, j + 1 - inset]].map(([x, y]) => [x * dx, 0, -y * dy]);
    const triangles = [];
    for (let k = 0; k < 4; k++) { const n = (k + 1) % 4;triangles.push([outer[k], outer[n], inner[n]], [outer[k], inner[n], inner[k]]); }
    triangles.push([inner[0], inner[1], inner[2]], [inner[0], inner[2], inner[3]]);
    const integral = () => triangles.reduce((sum, [a,b,c]) => sum + Math.abs((b[0]-a[0])*(c[2]-a[2])-(c[0]-a[0])*(b[2]-a[2])) / 2 * (a[1]+b[1]+c[1])/3, 0);
    const base = integral();inner.forEach(p => { p[1] = 1; });const coefficient = integral() - base;
    const peak = (h * dx * dy - base) / coefficient;inner.forEach(p => { p[1] = Math.max(0, peak); });
    cellVolumes.push(integral());for (const triangle of triangles) emit(...triangle);
    const floor=outer.map(p=>[p[0],0,p[2]]);emit(floor[0],floor[2],floor[1]);emit(floor[0],floor[3],floor[2]);
    for (let k=0;k<4;k++) {
      if (![j===0,i===nx-1,j===ny-1,i===0][k]) continue;
      const a=outer[k],b=outer[(k+1)%4],af=[a[0],0,a[2]],bf=[b[0],0,b[2]];emit(a,af,bf);emit(a,bf,b);
    }
  }
  return { positions, cellVolumes, volume: cellVolumes.reduce((a,b)=>a+b,0), maximumReliefFactor: 1 / (1 - 2 * inset + 4 * inset * inset / 3) };
}
